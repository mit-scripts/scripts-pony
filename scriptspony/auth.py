import subprocess
import threading
from decorator import decorator
import pwd
import re

import webob.exc

from . import keytab,log

state = threading.local()

def html(s):
    return '<html>'+s
# Monkeypatch to prevent webflash from escaping HTML conditionally
import webflash
html_escape = webflash.html_escape
webflash.html_escape = lambda s: s[len('<html>'):] if s.startswith('<html>') else html_escape(s)

def current_user():
    return state.username

def is_https():
    return state.https

def first_name():
    fullname = state.name
    bits = fullname.split()
    if len(bits) > 0:
        return bits[0]
    else:
        return None

def can_admin(locker):
    """Return true if the authentiated user can admin the named locker."""
    if not keytab.exists():
        cmd = ["/usr/local/bin/admof",'-noauth',locker,current_user()]
    else:
        # This quoting is safe because we've already ensured locker
        # doesn't contain dumb characters
        cmd = ["/usr/bin/pagsh","-c",
               "aklog athena sipb zone && /usr/local/bin/admof '%s' '%s'"
               %(locker,current_user())]
    admof = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = admof.communicate()
    if admof.returncode not in (33, 1):
         
        raise OSError(admof.returncode,err)
    if (out.strip() not in ("","yes","no") 
        or err.strip() not in ("","internal error: pioctl: No such file or directory")):
        log.err("admof failed for %s/%s: out='%s', err='%s'"
                % (locker, current_user(), out.strip(), err.strip()))
    return out.strip() == "yes" and admof.returncode == 33

class AuthError(webob.exc.HTTPForbidden):
    pass

LOCKER_PATTERN = re.compile(r'^(?:\w[\w.-]*\w|\w)$')

def validate_locker(locker):
    if not LOCKER_PATTERN.search(locker):
        raise AuthError("'%s' is not a valid locker."%locker)
    else:
        try:
            pwd.getpwnam(locker)
        except KeyError:
            raise AuthError(html("""The '%s' locker is not signed up for scripts.mit.edu; <a href="http://scripts.mit.edu/web/">sign it up</a> first."""%locker))
        if not can_admin(locker):
            raise AuthError("You cannot administer the '%s' locker!"%locker)

@decorator
def sensitive(func, locker,*args,**kw):
    """Wrap a function that takes a locker as the first argument
    such that it throws an AuthError unless the authenticated
    user can admin that locker."""
    validate_locker(locker)
    return func(locker.lower(),*args,**kw)

class ScriptsAuthMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        state.username = environ.get('REMOTE_USER',None)
        # We don't use SERVER_PORT because that lies and says 443 for
        # some reason
        state.https = environ.get('HTTP_HOST','').endswith(':444')
        state.name = environ.get('SSL_CLIENT_S_DN_CN','')
        keytab.auth()
        return self.app(environ,start_response)
