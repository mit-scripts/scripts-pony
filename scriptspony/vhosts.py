import ldap, ldap.sasl, ldap.filter
import re
import subprocess,os,pwd,getpass
import dns,dns.resolver,dns.exception
import httplib, socket
import hashlib
import random
import string
from decorator import decorator

import tg

from scripts.auth import (sensitive,team_sensitive,sudo_sensitive,current_user,
                          is_sudoing)
from scripts import keytab, log, hosts, auth
from . import mail
from .model import queue

LDAP_SERVERS = ['doppelganger', 'alter-ego', 'body-double']

def connect():
    global conn
    hostname = "{0}.mit.edu".format(LDAP_SERVERS[random.randint(0,2)])
    conn = ldap.initialize('ldap://{0}'.format(hostname))
    # Only try to use the keytab if we have one
    if keytab.exists():
        keytab.auth()
        auth = ldap.sasl.gssapi()
        conn.sasl_interactive_bind_s('',auth)
    else:
        conn.simple_bind_s()

@decorator
def reconnecting(func,*args,**kw):
    try:
        return func(*args,**kw)
    except ldap.SERVER_DOWN:
        connect()
        return func(*args,**kw)

@sensitive
@log.exceptions
@reconnecting
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
@reconnecting
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
@reconnecting
def set_path(locker,vhost,path):
    """Sets the path of an existing vhost owned by the locker."""
    path = validate_path(path)
    if vhost == locker+'.scripts.mit.edu':
        raise UserError("You cannot reconfigure "+vhost+"!")
    if is_host_reified(vhost):
        raise UserError("The host '%s' has special configuration; email scripts@mit.edu to make changes to it.")
    path = path.encode('utf-8')
    locker = locker.encode('utf-8')
    scriptsVhostName = get_vhost_name(locker,vhost)

    conn.modify_s(scriptsVhostName,[(ldap.MOD_REPLACE,'scriptsVhostDirectory',[path])])

    log.info("%s set path for vhost '%s' (locker '%s') to '%s'."
             % (current_user(),vhost,locker,path))
    # TODO: Check path existance and warn if we know the web_scripts path
    #       doesn't exist
    # TODO: also check for index files or .htaccess and warn if none are there

HOSTNAME_PATTERN = re.compile(r'^(?:[*][.])?(?:[\w-]+[.])+[a-z]+$')

@sudo_sensitive
@log.exceptions
def request_vhost(locker,hostname,path,user=None,desc=''):
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
        t = queue.Ticket.create(locker,hostname,path,requestor=user,purpose=desc)
        short = hostname[:-len('.mit.edu')]
        mail.create_ticket(subject="scripts-vhosts CNAME request: %s"%short,
                           body="""Heyas,

%(user)s requested %(hostname)s for locker '%(locker)s' path %(path)s.
Go to %(url)s to approve it.

Purpose:
%(desc)s

Love,
~Scripts Pony
""" % dict(short=short,user=user,locker=locker,hostname=hostname,desc=desc,
           path=path,url=tg.request.host_url+tg.url('/ticket/%s'%t.id)),
                           id=t.id, requestor=user)
        message = "We will request the hostname %s; mit.edu hostnames generally take 2-3 business days to become active." % hostname
    else:
        # Actually create the vhost
        actually_create_vhost(locker,hostname,path)
    if is_sudoing():
        sudobit = '+scripts-pony-acl'
        forbit = ' (for %s)' % user
    else:
        sudobit = ''
        forbit = ''
    logmessage = "%s%s requested %s for locker '%s' path '%s'%s (Purpose: %s)" % (
        current_user(), sudobit, hostname, locker,path,forbit,desc)

    log.info(logmessage)
    return message

def validate_path(path):
    """Throw a UserError if path is not valid for a vhost path."""
    path = path.strip()
    if (not path.startswith('/')
        and '..' not in path.split('/')
        and (path == '.' or '.' not in path.split('/'))
        and '//' not in path):
        if path.endswith('/'):
            path = path[:-1]
        if path == '':
            path = '.'
        return path
    else:
        raise UserError("'%s' is not a valid path." % path)

def generate_hostname_check_file(hostname,locker):
    """Generate a unique-ish hash for a given hostname and locker"""
    return "scripts_%s.html" % hashlib.sha1(hostname.lower() + locker).hexdigest()[:10]

def generate_random_hostname():
    """Generates a random string for use as a subdomain"""
    return ''.join(random.choice(string.ascii_lowercase) for x in xrange(9))

def validate_hostname(hostname,locker):
    hostname = hostname.lower().encode('utf-8')
    if not HOSTNAME_PATTERN.search(hostname):
        if '.' not in hostname:
            raise UserError("'%s' is not an absolute hostname.  Do you mean '%s.mit.edu'?" % (hostname,hostname))
        else:
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
            if hosts.points_at_scripts(hostname) and is_sudoing():
                # It was manually transfered to scripts; if it's not an
                # existing vhost, we good.
                reqtype = 'manual'
            else:
                raise UserError("'%s' already exists. Please choose another name or contact scripts@mit.edu if you wish to transfer the hostname to scripts."
                            % hostname)
        else:
            raise RuntimeError("DNS query should never return successfully!")
        stella_cmd = subprocess.Popen(["/usr/bin/stella", "-u", "-noauth", hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = stella_cmd.communicate()
        if stella_cmd.returncode != 1:
            # Then its reserved, deleted, etc.
            status = "Unknown"
            for line in out.split("\n"):
                if "Status:" in line:
                    status = line.split(" ")[-2]
            raise UserError("'%s' is not available; it currently has status %s. Please choose another name or contact scripts@mit.edu if you wish to transfer the hostname to scripts." % (hostname, status))

    else:
        reqtype='external'
        if not hosts.points_at_scripts(hostname):
            # Check if our magic file is there.
            check_file = generate_hostname_check_file(hostname,locker)
            try:
                # If this is a wildcard, pick some random domain to test.
                # We expect that *all* subdomains will match the same host if you're
                # using a wildcard.
                test_hostname = hostname
                if test_hostname[0:2] == '*.':
                    test_hostname = generate_random_hostname() + test_hostname[1:]
                connection = httplib.HTTPConnection(test_hostname,timeout=5) # Shortish timeout - 5 seconds
                connection.request("HEAD", "/%s" % check_file)
                status = connection.getresponse()
                connection.close()
                if status.status != httplib.OK:
                    raise UserError(auth.html("'%s' does not point at scripts-vhosts. If you want to continue anyway, please create a file called '%s' in the root directory of the site. See <a href='http://scripts.mit.edu/faq/132/can-i-add-a-vhost-before-i-point-my-domain-at-scripts' target='_blank'>the FAQ</a> for more information."
                                    % (hostname,check_file)))
            except socket.gaierror:
                raise UserError("'%s' does not exist." % hostname)
            except (httplib.HTTPException, socket.error):
                raise UserError(auth.html("'%s' does not point at scripts-vhosts, and appears to have no running webserver. Please see <a href='http://scripts.mit.edu/faq/132/can-i-add-a-vhost-before-i-point-my-domain-at-scripts' target='_blank'>the FAQ</a> for more information."
                                % hostname))

    return hostname,reqtype

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

@reconnecting
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
                          ldap.filter.filter_format('(&(objectClass=scriptsVhost)(|(scriptsVhostName=%s)(scriptsVhostAlias=%s))(!(|(scriptsVhostName=notfound.example.com)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu))))',[p,p,locker]),['scriptsVhostAccount'],False)
        if len(res) != 0:
            raise UserError("'%s' is already a wildcard hostname on scripts.mit.edu."
                            % hostname)

@team_sensitive
@reconnecting
def actually_create_vhost(locker,hostname,path):
    locker=locker.encode('utf-8')
    hostname=hostname.encode('utf-8')
    path=path.encode('utf-8')
    
    check_if_already_exists(hostname,locker)
    scriptsVhostName = ldap.filter.filter_format("scriptsVhostName=%s,ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",[hostname])
    if hostname.endswith('.mit.edu'):
        alias = hostname[:-len('.mit.edu')]
    else:
        alias = None
    uid,gid = get_uid_gid(locker)
    account = ldap.filter.filter_format('uid=%s,ou=People,dc=scripts,dc=mit,dc=edu',[locker])

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
@reconnecting
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
    scriptsVhostName = get_vhost_name(locker,hostname)
    conn.modify_s(scriptsVhostName,[(ldap.MOD_ADD,'scriptsVhostAlias',
                                     [alias])])
    log.info("%s added alias '%s' to '%s' (locker '%s')."
             % (current_user(),alias,hostname,locker))

@reconnecting
def get_vhost_name(locker,vhost):
    res=conn.search_s('ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
                      ldap.SCOPE_ONELEVEL,
                      ldap.filter.filter_format('(&(objectClass=scriptsVhost)(scriptsVhostAccount=uid=%s,ou=People,dc=scripts,dc=mit,dc=edu)(scriptsVhostName=%s))',[locker,vhost]),['scriptsVhostDirectory'],False)
    scriptsVhostName = res[0][0]
    return scriptsVhostName
