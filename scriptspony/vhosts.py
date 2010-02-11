import ldap, ldap.sasl, ldap.filter
import re
import socket,subprocess,os,pwd
import smtplib
from email.mime.text import MIMEText

from .auth import sensitive,current_user
from . import keytab, log

def connect():
    global conn
    conn = ldap.initialize('ldap://localhost')
    # Only try to use the keytab if we have one
    if keytab.exists():
        keytab.auth()
        auth = ldap.sasl.gssapi()
        conn.sasl_interactive_bind_s('',auth)
    else:
        conn.simple_bind_s()

@sensitive
@log.exceptions
def list_vhosts(locker):
    """Return a list of (vhost,directory) for the given locker.

    The directory is relative to web_scripts or Scripts/*/"""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu))',[locker]),['scriptsVhostName','scriptsVhostDirectory'])
    return [(m['scriptsVhostName'][0],m['scriptsVhostDirectory'][0])
            for i,m in res]


@sensitive
@log.exceptions
def get_path(locker,hostname):
    """Return a the path for the given hostname.

    The directory is relative to web_scripts or Scripts/*/"""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))',[locker,hostname]),['scriptsVhostDirectory'])
    return res[0][1]['scriptsVhostDirectory'][0]

@sensitive
@log.exceptions
def set_path(locker,vhost,path):
    """Sets the path of an existing vhost owned by the locker."""
    validate_path(path)
    if vhost == locker+'.scripts.mit.edu':
        raise UserError("You cannot reconfigure "+vhost+"!")
    if is_host_reified(vhost):
        raise UserError("The host '%s' has special configuration; email scripts@mit.edu to make changes to it.")
    if path.endswith('/'):
        path = path[:-1]
    path = path.encode('utf-8')
    locker = locker.encode('utf-8')
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))',[locker,vhost]),['scriptsVhostDirectory'],False)
    scriptsVhostName = res[0][0]
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=apacheConfig)(apacheServerName=%s))',[vhost]),['apacheDocumentRoot'],False)
    apacheVhostName = res[0][0]
    web_scriptsPath = get_web_scripts_path(locker,path)

    conn.modify_s(scriptsVhostName,[(ldap.MOD_REPLACE,'scriptsVhostDirectory',[path])])
    conn.modify_s(apacheVhostName,[(ldap.MOD_REPLACE,'apacheDocumentRoot',[web_scriptsPath])])

    log.info("%s set path for vhost '%s' to '%s' for the %s locker."
             % (current_user(),vhost,path,locker))
    # TODO: Check path existance and warn if we know the web_scripts path
    #       doesn't exist
    # TODO: also check for index files or .htaccess and warn if none are there

HOSTNAME_PATTERN = re.compile(r'^[\w-]+(?:[.][\w-]+)+$')

@sensitive
@log.exceptions
def request_vhost(locker,hostname,path):
    """Request hostname as a vhost for the given locker and path.

    Throws a UserError if the request is invalid, otherwise returns
    a human-readable status message and sends a zephyr."""
    locker = locker.encode('utf-8')
    hostname = hostname.lower().encode('utf-8')
    path = path.encode('utf-8')
    validate_path(path)
    if not HOSTNAME_PATTERN.search(hostname):
        raise UserError("'%s' is not a valid hostname." % hostname)
    message = "The hostname '%s' is now configured." % hostname
    if hostname.endswith(".scripts.mit.edu"):
        reqtype = 'subscripts'
        if not hostname.endswith("."+locker+".scripts.mit.edu"):
            raise UserError("'%s' is not a valid hostname for the '%s' locker." % (hostname,locker))
    elif hostname.endswith(".mit.edu"):
        reqtype='moira'
        if hostname.count('.') != 2:
            raise UserError("'%s' has too many dots for a mit.edu hostname."
                            % hostname)
        # stella
        message = "We will request the hostname %s; mit.edu hostnames generally take 2-3 business days to become active." % hostname
    else:
        reqtype='external'
        failed = False
        try:
            if (socket.gethostbyname(hostname+'.')
                != socket.gethostbyname("scripts-vhosts.mit.edu.")):
                failed=True
        except socket.gaierror:
            failed=True
        if failed:
            raise UserError("'%s' does not point at scripts-vhosts."
                            %hostname)
    # Actually create the vhost
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostName=%s))',[hostname]),['scriptsVhostDirectory'],False)
    if len(res) != 0:
        raise UserError("'%s' is already a hostname on scripts.mit.edu."
                        % hostname)
    scriptsVhostName = ldap.filter.filter_format("scriptsVhostName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",[hostname])
    apacheServerName = ldap.filter.filter_format("apacheServerName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",[hostname])
    if hostname.endswith('.mit.edu'):
        alias = hostname[:-len('.mit.edu')]
    else:
        alias = None
    web_scriptsPath = get_web_scripts_path(locker,path)
    uid,gid = get_uid_gid(locker)
    account = ldap.filter.filter_format('uid=%s,ou=People,dc=scripts,dc=mit,dc=edu',[locker])
    logmessage = "%s requested %s for locker '%s' path '%s'" % (
        current_user(), hostname, locker,path)

    conn.add_s(apacheServerName,[('objectClass',['apacheConfig','top']),
                                 ('apacheServerName',[hostname]),
                                 ('apacheServerAlias',[alias] if alias else []),
                                 ('apacheDocumentRoot',[web_scriptsPath]),
                                 ('apacheSuexecUid',[str(uid)]),
                                 ('apacheSuexecGid',[str(gid)])])
    conn.add_s(scriptsVhostName,[('objectClass',['scriptsVhost','top']),
                                 ('scriptsVhostName',[hostname]),
                                 ('scriptsVhostAlias',[alias] if alias else []),
                                 ('scriptsVhostAccount',[account]),
                                 ('scriptsVhostDirectory',[path])])

    log.info(logmessage)
    if reqtype == 'moira':
        sendmail(locker,hostname,path)
    return message

def validate_path(path):
    """Throw a UserError if path is not valid for a vhost path."""
    if (not path.startswith('/')
        and '..' not in path.split('/')
        and '.' not in path.split('/')
        and '//' not in path):
        return
    else:
        raise UserError("'%s' is not a valid path." % path)

@log.exceptions
def get_web_scripts_path(locker,path):
    """Return the web_scripts filesystem path for a given locker and vhost path."""
    return os.path.join(conn.search_s('ou=People,dc=scripts,dc=mit,dc=edu',ldap.SCOPE_ONELEVEL,ldap.filter.filter_format('(uid=%s)',[locker]))[0][1]['homeDirectory'][0],path)

def get_uid_gid(locker):
    """Get the scripts uid and gid for a locker."""
    p = pwd.getpwnam(locker)
    return (p.pw_uid,p.pw_gid)

@log.exceptions
def is_host_reified(hostname):
    """Return true if the given hostname is reified."""
    httpd = subprocess.Popen(["/usr/sbin/httpd","-S"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = httpd.communicate()
    if httpd.returncode != 0:
        log.err("Pony: httpd -S returned %d!" % httpd.returncode)
    return ("namevhost %s " % hostname) in out

class UserError(log.ExpectedException):
    pass

def sendmail(locker,hostname,path):
    """Send mail for MIT vhost requests."""
    # Send manual mail for this case
    fromaddr = "%s@mit.edu" % current_user()
    toaddr = "scripts@mit.edu"
    msg = MIMEText("""%s wants %s to point to %s in the %s locker.

(The vhost is already configured.)

Sincerely,
~Scripts Pony""" % (fromaddr,hostname,path,locker))
    msg['Subject'] = "%s hostname request" % hostname
    msg['From'] = fromaddr
    msg['To'] = toaddr
    s = smtplib.SMTP()
    s.connect()
    s.sendmail(fromaddr,[toaddr],msg.as_string())
    s.quit()
