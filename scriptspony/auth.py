import subprocess
import threading
from decorator import decorator
import re

import webob.exc

state = threading.local()

def current_user():
    ending = '@MIT.EDU'
    uname = state.email
    if uname is None or not uname.endswith(ending):
        return None
    else:
        return uname[:-len(ending)]

def first_name():
    fullname = state.name
    bits = fullname.split()
    if len(bits) > 0:
        return bits[0]
    else:
        return None

def can_admin(locker):
    admof = subprocess.Popen(["/usr/local/bin/admof","-noauth",locker,current_user()],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = admof.communicate()
    if admof.returncode not in (33, 1):
        raise OSError(admof.returncode,err)
    return out.strip() == "yes" and admof.returncode == 33

class AuthError(webob.exc.HTTPForbidden):
    pass

LOCKER_PATTERN = re.compile(r'^(?:\w[\w.-]*\w|\w)$')

@decorator
def sensitive(func, locker,*args,**kw):
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
        state.email = environ.get('SSL_CLIENT_S_DN_Email',None)
        state.name = environ.get('SSL_CLIENT_S_DN_CN','')
        return self.app(environ,start_response)
