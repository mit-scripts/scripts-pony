import ldap
import re
import socket,subprocess,os.path,pwd
import smtplib
from email.mime.text import MIMEText

from .auth import sensitive,current_user

def connect():
    global conn
    conn = ldap.open('localhost')
    conn.simple_bind_s(who, cred)

@sensitive
def list_vhosts(locker):
    """Return a list of (vhost,directory) for the given locker.

    The directory is relative to web_scripts or Scripts/*/"""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      '(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu))'%ldap.dn.escape_dn_chars(locker),['scriptsVhostName','scriptsVhostDirectory'])
    return [(m['scriptsVhostName'][0],m['scriptsVhostDirectory'][0])
            for i,m in res]


@sensitive
def get_path(locker,hostname):
    """Return a the path for the given locker.

    The directory is relative to web_scripts or Scripts/*/"""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      '(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))'%(ldap.dn.escape_dn_chars(locker),ldap.dn.escape_dn_chars(hostname)),['scriptsVhostDirectory'])
    return res[0][1]['scriptsVhostDirectory'][0]

@sensitive
def set_path(locker,vhost,path):
    """Sets the path of an existing vhost owned by the locker."""
    validate_path(path)
    if vhost != locker+'.scripts.mit.edu':
        raise UserError("You cannot reconfigure "+vhost+"!")
    if path.endswith('/'):
        path = path[:-1]
    path = path.encode('utf-8')
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      '(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))'%(ldap.dn.escape_dn_chars(locker),ldap.dn.escape_dn_chars(vhost)),['scriptsVhostDirectory'],False)
    scriptsVhostName = res[0][0]
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      '(&(objectClass=apacheConfig)(apacheServerName=%s))'%(ldap.dn.escape_dn_chars(vhost)),['apacheDocumentRoot'],False)
    apacheVhostName = res[0][0]
    conn.modify_s(scriptsVhostName,[(ldap.MOD_REPLACE,'scriptsVhostDirectory',[path])])
    web_scriptsPath = get_web_scripts_path(locker,path)
    conn.modify_s(apacheVhostName,[(ldap.MOD_REPLACE,'apacheDocumentRoot',[web_scriptsPath])])
    # TODO: Check path existance and warn if we know the web_scripts path
    #       doesn't exist
    # TODO: also check for index files or .htaccess and warn if none are there

HOSTNAME_PATTERN = re.compile(r'^[\w-]+(?:[.][\w-]+)+$')

@sensitive
def request_vhost(locker,hostname,path):
    locker = locker.encode('utf-8')
    hostname = hostname.lower().encode('utf-8')
    path = path.encode('utf-8')
    validate_path(path)
    if not HOSTNAME_PATTERN.search(hostname):
        raise UserError("'%s' is not a valid hostname." % hostname)
    message = "The hostname %s is now configured." % hostname
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
        # Send manual mail for this case
        fromaddr = "%s@mit.edu" % current_user()
        toaddr = "xavid@mit.edu"
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
        message = "We will request the hostname %s; mit.edu hostnames generally take 2-3 business days to become active." % hostname
    else:
        reqtype='external'
        if (socket.gethostbyname(hostname+'.')
            != socket.gethostbyname("scripts-vhosts.mit.edu")):
            raise UserError("'%s' does not point at scripts-vhosts.")
    # Actually create the vhost
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      '(&(objectClass=scriptsVhost)(scriptsVhostName=%s))'%(ldap.dn.escape_dn_chars(hostname)),['scriptsVhostDirectory'],False)
    if len(res) != 0:
        raise UserError("'%s' is already a hostname on scripts.mit.edu."
                        % hostname)
    scriptsVhostName = "scriptsVhostName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu" % ldap.dn.escape_dn_chars(hostname)
    apacheServerName = "apacheServerName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu" % ldap.dn.escape_dn_chars(hostname)
    if hostname.endswith('.mit.edu'):
        alias = hostname[:-len('.mit.edu')]
    else:
        alias = None
    web_scriptsPath = get_web_scripts_path(locker,path)
    uid,gid = get_uid_gid(locker)
    account = 'uid=%s,ou=People,dc=scripts,dc=mit,dc=edu' % ldap.dn.escape_dn_chars(locker)
    logmessage = "%s requested %s for locker %s" % (
        current_user(), hostname, locker)
    try:
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
    except:
        zwrite(hostname,logmessage + "; but it failed.")
        raise
    else:
        zwrite(hostname,logmessage)
        return message

def validate_path(path):
    if (not path.startswith('/')
        and '..' not in path.split('/')
        and '.' not in path.split('/')
        and '//' not in path):
        return
    else:
        raise UserError("'%s' is not a valid path." % path)

def get_web_scripts_path(locker,path):
    return os.path.realpath('/mit/'+locker+'/web_scripts/'+path)

def get_uid_gid(locker):
    p = pwd.getpwnam(locker)
    return (p.pw_uid,p.pw_gid)

class UserError(Exception):
    pass

def zwrite(hostname,logmessage):
    zwrite = subprocess.Popen(["/usr/bin/zwrite","-d","-c","xavetest","-i",
                               "pony","-s",hostname,"-m",logmessage])
