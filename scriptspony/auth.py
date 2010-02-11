import subprocess
import threading
from decorator import decorator
import re

import webob.exc

from . import keytab,log

state = threading.local()

def current_user():
    return state.username

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
               "aklog && /usr/local/bin/admof '%s' '%s'"
               %(locker,current_user())]
    admof = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = admof.communicate()
    if admof.returncode not in (33, 1):
         
        raise OSError(admof.returncode,err)
    if (out.strip() not in ("","yes","no") 
        or err.strip() not in ("","internal error: pioctl: No such file or directory")):
        log.err("admof failed for %s/%s: out='%s', err='%s'"
                % (locker, current_user(), out.strip(), err.strip()))
    return out.strip() == "yes" and admof.returncode == 33 and current_user()=='xavid'

class AuthError(webob.exc.HTTPForbidden):
    pass

LOCKER_PATTERN = re.compile(r'^(?:\w[\w.-]*\w|\w)$')

@decorator
def sensitive(func, locker,*args,**kw):
    """Wrap a function that takes a locker as the first argument
    such that it throws an AuthError unless the authenticated
    user can admin that locker."""
    if not LOCKER_PATTERN.search(locker):
        raise AuthError("'%s' is not a valid locker."%locker)
    elif not can_admin(locker):
        raise AuthError("You cannot administer the '%s' locker!"%locker)
    else:
        return func(locker.lower(),*args,**kw)

class ScriptsAuthMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        state.username = environ.get('REMOTE_USER',None)
        state.name = environ.get('SSL_CLIENT_S_DN_CN','')
        return self.app(environ,start_response)
