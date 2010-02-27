import ldap, ldap.sasl, ldap.filter
import re
import subprocess,os,pwd,getpass
import dns,dns.resolver,dns.exception

import tg

from .auth import sensitive,team_sensitive,current_user
from . import keytab, log, util, mail
from .model import queue

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


@team_sensitive
@log.exceptions
def get_path(locker,hostname):
    """Return a the path for the given hostname.

    The directory is relative to web_scripts or Scripts/*/"""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))',[locker,hostname]),['scriptsVhostDirectory'])
    try:
        return res[0][1]['scriptsVhostDirectory'][0]
    except IndexError:
        raise UserError("The hostname '%s' does not exist for the '%s' locker."
                        % (hostname,locker))

@sensitive
@log.exceptions
def set_path(locker,vhost,path):
    """Sets the path of an existing vhost owned by the locker."""
    path = validate_path(path)
    if vhost == locker+'.scripts.mit.edu':
        raise UserError("You cannot reconfigure "+vhost+"!")
    if is_host_reified(vhost):
        raise UserError("The host '%s' has special configuration; email scripts@mit.edu to make changes to it.")
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

    log.info("%s set path for vhost '%s' (locker '%s') to '%s'."
             % (current_user(),vhost,locker,path))
    # TODO: Check path existance and warn if we know the web_scripts path
    #       doesn't exist
    # TODO: also check for index files or .htaccess and warn if none are there

HOSTNAME_PATTERN = re.compile(r'^(?:[\w-]+[.])+[a-z]+$')

@sensitive
@log.exceptions
def request_vhost(locker,hostname,path):
    """Request hostname as a vhost for the given locker and path.

    Throws a UserError if the request is invalid, otherwise returns
    a human-readable status message and sends a zephyr."""
    locker = locker.encode('utf-8')
    hostname = hostname.lower().encode('utf-8')
    path = path.encode('utf-8')
    path = validate_path(path)
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
        try:
            dns.resolver.query(hostname+'.', 0)
        except dns.resolver.NXDOMAIN:
            pass
        except dns.exception.Timeout:
            raise
        except dns.exception.DNSException:
            raise UserError("'%s' already exists. Please choose another name or contact scripts@mit.edu  if you wish to transfer the hostname to scripts."
                            % hostname)
        else:
            raise RuntimeError("DNS query should never return successfully!")
        # should use stella to check for reserved/deleted hosts and aliases
        # stella
        message = "We will request the hostname %s; mit.edu hostnames generally take 2-3 business days to become active." % hostname
    else:
        reqtype='external'
        if not util.points_at_scripts(hostname):
            raise UserError("'%s' does not point at scripts-vhosts."
                            %hostname)
    if reqtype == 'moira':
        # actually_create_vhost does this check for other reqtypes
        check_if_already_exists(hostname)
        t = queue.Ticket.create(locker,hostname,path)
        short = hostname[:-len('.mit.edu')]
        mail.create_ticket(subject="scripts-vhosts CNAME request: %s"%short,
                           body="""Heyas,

%(user)s requested %(hostname)s for locker '%(locker)s' path %(path)s.
Go to %(url)s to approve it.

Love,
~Scripts Pony
""" % dict(short=short,user=current_user(),locker=locker,hostname=hostname,
           path=path,url=tg.request.host_url+tg.url('/ticket/%s'%t.id)),
                           id=t.id, requestor=current_user())
    else:
        # Actually create the vhost
        actually_create_vhost(locker,hostname,path)
    logmessage = "%s requested %s for locker '%s' path '%s'" % (
        current_user(), hostname, locker,path)

    log.info(logmessage)
    return message

def validate_path(path):
    """Throw a UserError if path is not valid for a vhost path."""
    if (not path.startswith('/')
        and '..' not in path.split('/')
        and '.' not in path.split('/')
        and '//' not in path):
        if path.endswith('/'):
            path = path[:-1]
        return path
    else:
        raise UserError("'%s' is not a valid path." % path)

@log.exceptions
def get_web_scripts_path(locker,path):
    """Return the web_scripts filesystem path for a given locker and vhost path."""
    web_scriptsPath = os.path.join(conn.search_s('ou=People,dc=scripts,dc=mit,dc=edu',ldap.SCOPE_ONELEVEL,ldap.filter.filter_format('(uid=%s)',[locker]))[0][1]['homeDirectory'][0],'web_scripts',path)
    if web_scriptsPath.endswith('/'):
        web_scriptsPath = web_scriptsPath[:-1]
    return web_scriptsPath

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

def check_if_already_exists(hostname):
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(|(scriptsVhostName=%s)(scriptsVhostAlias=%s)))',[hostname,hostname]),['scriptsVhostDirectory'],False)
    if len(res) != 0:
        raise UserError("'%s' is already a hostname on scripts.mit.edu."
                        % hostname)

@team_sensitive
def actually_create_vhost(locker,hostname,path):
    locker=locker.encode('utf-8')
    hostname=hostname.encode('utf-8')
    path=path.encode('utf-8')
    
    check_if_already_exists(hostname)
    scriptsVhostName = ldap.filter.filter_format("scriptsVhostName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",[hostname])
    apacheServerName = ldap.filter.filter_format("apacheServerName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",[hostname])
    if hostname.endswith('.mit.edu'):
        alias = hostname[:-len('.mit.edu')]
    else:
        alias = None
    web_scriptsPath = get_web_scripts_path(locker,path)
    uid,gid = get_uid_gid(locker)
    account = ldap.filter.filter_format('uid=%s,ou=People,dc=scripts,dc=mit,dc=edu',[locker])

    conn.add_s(apacheServerName,
               [('objectClass',['apacheConfig','top']),
                ('apacheServerName',[hostname])]
               +
               ([('apacheServerAlias',alias)] if alias else [])
               +
               [('apacheDocumentRoot',[web_scriptsPath]),
                ('apacheSuexecUid',[str(uid)]),
                ('apacheSuexecGid',[str(gid)])])
    conn.add_s(scriptsVhostName,
               [('objectClass',['scriptsVhost','top']),
                ('scriptsVhostName',[hostname])]
               +
               ([('scriptsVhostAlias',alias)] if alias else [])
               +
               [('scriptsVhostAccount',[account]),
                ('scriptsVhostDirectory',[path])])
