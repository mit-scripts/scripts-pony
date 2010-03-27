import ldap, ldap.sasl, ldap.filter
import re
import subprocess,os,pwd,getpass
import dns,dns.resolver,dns.exception

import tg

from scripts.auth import (sensitive,team_sensitive,sudo_sensitive,current_user,
                          is_sudoing)
from scripts import keytab, log, hosts
from . import mail
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
    """Return a list of (vhost,aliases,directory) for the given locker.

    The directory is relative to web_scripts or Scripts/*/"""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu))',[locker]),['scriptsVhostName','scriptsVhostDirectory','scriptsVhostAlias'])
    return [(m['scriptsVhostName'][0],m.get('scriptsVhostAlias',[]),m['scriptsVhostDirectory'][0])
            for i,m in res]


@team_sensitive
@log.exceptions
def get_path(locker,hostname):
    """Return a the path for the given hostname.

    The directory is relative to web_scripts or Scripts/*/"""
    return get_vhost_info(locker,hostname)[0]

@team_sensitive
@log.exceptions
def get_vhost_info(locker,hostname):
    """Return path,aliases for the given hostname."""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))',[locker,hostname]),['scriptsVhostDirectory','scriptsVhostAlias'])
    try:
        return (res[0][1]['scriptsVhostDirectory'][0],
                res[0][1].get('scriptsVhostAlias',[]))
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
    scriptsVhostName,apacheVhostName = get_vhost_names(locker,vhost)
    web_scriptsPath = get_web_scripts_path(locker,path)

    conn.modify_s(scriptsVhostName,[(ldap.MOD_REPLACE,'scriptsVhostDirectory',[path])])
    conn.modify_s(apacheVhostName,[(ldap.MOD_REPLACE,'apacheDocumentRoot',[web_scriptsPath])])

    log.info("%s set path for vhost '%s' (locker '%s') to '%s'."
             % (current_user(),vhost,locker,path))
    # TODO: Check path existance and warn if we know the web_scripts path
    #       doesn't exist
    # TODO: also check for index files or .htaccess and warn if none are there

HOSTNAME_PATTERN = re.compile(r'^(?:[\w-]+[.])+[a-z]+$')

@sudo_sensitive
@log.exceptions
def request_vhost(locker,hostname,path,user=None):
    """Request hostname as a vhost for the given locker and path.

    Throws a UserError if the request is invalid, otherwise returns
    a human-readable status message and sends a zephyr."""
    locker = locker.encode('utf-8')
    hostname,reqtype = validate_hostname(hostname,locker)
    path = path.encode('utf-8')
    path = validate_path(path)
    message = "The hostname '%s' is now configured." % hostname

    if user is None:
        user = current_user()
    
    if reqtype == 'moira':
        # actually_create_vhost does this check for other reqtypes
        check_if_already_exists(hostname,locker)
        t = queue.Ticket.create(locker,hostname,path,requestor=user)
        short = hostname[:-len('.mit.edu')]
        mail.create_ticket(subject="scripts-vhosts CNAME request: %s"%short,
                           body="""Heyas,

%(user)s requested %(hostname)s for locker '%(locker)s' path %(path)s.
Go to %(url)s to approve it.

Love,
~Scripts Pony
""" % dict(short=short,user=user,locker=locker,hostname=hostname,
           path=path,url=tg.request.host_url+tg.url('/ticket/%s'%t.id)),
                           id=t.id, requestor=user)
        message = "We will request the hostname %s; mit.edu hostnames generally take 2-3 business days to become active." % hostname
    else:
        # Actually create the vhost
        actually_create_vhost(locker,hostname,path)
    if is_sudoing():
        sudobit = '+sudo'
        forbit = ' (for %s)' % user
    else:
        sudobit = ''
        forbit = ''
    logmessage = "%s%s requested %s for locker '%s' path '%s'%s" % (
        current_user(), sudobit, hostname, locker,path,forbit)

    log.info(logmessage)
    return message

def validate_path(path):
    """Throw a UserError if path is not valid for a vhost path."""
    path = path.strip()
    if (not path.startswith('/')
        and '..' not in path.split('/')
        and '.' not in path.split('/')
        and '//' not in path):
        if path.endswith('/'):
            path = path[:-1]
        return path
    else:
        raise UserError("'%s' is not a valid path." % path)

def validate_hostname(hostname,locker):
    hostname = hostname.lower().encode('utf-8')
    if not HOSTNAME_PATTERN.search(hostname):
        raise UserError("'%s' is not a valid hostname." % hostname)

    if hostname.endswith(".scripts.mit.edu"):
        reqtype = 'subscripts'
        if not hostname.endswith("."+locker+".scripts.mit.edu"):
            raise UserError("'%s' is not a valid hostname for the '%s' locker." % (hostname,locker))
    elif hostname.endswith(".mit.edu"):
        reqtype='moira'
        if hostname.count('.') != 2:
            raise UserError("'%s' has too many dots for a mit.edu hostname."
                            % hostname)
        if not hostname[0].isalpha():
            raise UserError(".mit.edu hostnames must start with a letter.")
        if hostname[-len(".mit.edu")-1] == '-':
            raise UserError(".mit.edu hostnames cannot end with a dash.")
        if '_' in hostname:
            raise UserError(".mit.edu hostnames cannot contain an underscore.")
        try:
            dns.resolver.query(hostname+'.', 0)
        except dns.resolver.NXDOMAIN:
            pass
        except dns.exception.Timeout:
            raise
        except dns.exception.DNSException:
            raise UserError("'%s' already exists. Please choose another name or contact scripts@mit.edu if you wish to transfer the hostname to scripts."
                            % hostname)
        else:
            raise RuntimeError("DNS query should never return successfully!")
        # TODO: should use stella to check for reserved/deleted hosts
        # and aliases stella
    else:
        reqtype='external'
        if not hosts.points_at_scripts(hostname):
            raise UserError("'%s' does not point at scripts-vhosts."
                            %hostname)

    return hostname,reqtype

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

def check_if_already_exists(hostname,locker):
    """Raise a UserError if hostname already exists on scripts,
    unless it only exists as a wildcard hostname owned by locker."""
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(|(scriptsVhostName=%s)(scriptsVhostAlias=%s)))',[hostname,hostname]),['scriptsVhostDirectory'],False)
    if len(res) != 0:
        raise UserError("'%s' is already a hostname on scripts.mit.edu."
                        % hostname)
    bits = hostname.split('.')
    possibilities = ['*.'+'.'.join(bits[x:]) for x in xrange(1,len(bits))]
    for p in possibilities:
        res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                          ldap.SCOPE_ONELEVEL,
                          ldap.filter.filter_format('(&(objectClass=scriptsVhost)(|(scriptsVhostName=%s)(scriptsVhostAlias=%s)))',[p,p]),['scriptsVhostAccount'],False)
        if len(res) != 0 and res[0][1]['scriptsVhostAccount'][0] != 'uid=%s,ou=People,dc=scripts,dc=mit,dc=edu' % locker:
            raise UserError("'%s' is already a hostname on scripts.mit.edu."
                            % hostname)

@team_sensitive
def actually_create_vhost(locker,hostname,path):
    locker=locker.encode('utf-8')
    hostname=hostname.encode('utf-8')
    path=path.encode('utf-8')
    
    check_if_already_exists(hostname,locker)
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

@sensitive
@log.exceptions
def add_alias(locker,hostname,alias):
    locker = locker.encode('utf-8')
    hostname = hostname.lower().encode('utf-8')
    if hostname.endswith('.mit.edu'):
        raise UserError("You can't add aliases to .mit.edu hostnames!")
    if alias.lower().encode('utf-8').endswith('.mit.edu'):
        raise UserError("You can't add .mit.edu aliases to non-.mit.edu hostnames!")
    alias,reqtype = validate_hostname(alias,locker)
    if reqtype != 'external':
        raise RuntimeError("We didn't catch that something wasn't a .mit.edu hostname.")
    
    check_if_already_exists(alias,locker)

    # If we got here, we're good
    scriptsVhostName,apacheVhostName = get_vhost_names(locker,hostname)
    conn.modify_s(scriptsVhostName,[(ldap.MOD_ADD,'scriptsVhostAlias',
                                     [alias])])
    conn.modify_s(apacheVhostName,[(ldap.MOD_ADD,'apacheServerAlias',
                                     [alias])])
    log.info("%s added alias '%s' to '%s' (locker '%s')."
             % (current_user(),alias,hostname,locker))

def get_vhost_names(locker,vhost):
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))',[locker,vhost]),['scriptsVhostDirectory'],False)
    scriptsVhostName = res[0][0]
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=apacheConfig)(apacheServerName=%s))',[vhost]),['apacheDocumentRoot'],False)
    apacheVhostName = res[0][0]
    return (scriptsVhostName,apacheVhostName)
