import subprocess
import threading
from decorator import decorator
import re

import webob.exc

from . import keytab

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
    cmd = ["/usr/local/bin/admof"]
    if not keytab.exists():
        cmd.append('-noauth')
    cmd += [locker,current_user()]
    admof = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = admof.communicate()
    if admof.returncode not in (33, 1):
        raise OSError(admof.returncode,err)
    return out.strip() == "yes" and admof.returncode == 33 and current_user()=='xavid'

class AuthError(webob.exc.HTTPForbidden):
    pass

LOCKER_PATTERN = re.compile(r'^(?:\w[\w.-]*\w|\w)$')

@decorator
def sensitive(func, locker,*args,**kw):
    """Wrap a function that takes a locker as the first argument
    such that it throws an AuthError unless the authenticated
    user can admin that locker."""
    if not can_admin(locker):
        raise AuthError("You cannot administer the '%s' locker!"%locker)
    elif not LOCKER_PATTERN.search(locker):
        raise AuthError("'%s' is not a valid locker."%locker)
    else:
        return func(locker.lower(),*args,**kw)

class ScriptsAuthMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        state.username = environ.get('REMOTE_USER',None)
        state.name = environ.get('SSL_CLIENT_S_DN_CN','')
        return self.app(environ,start_response)
