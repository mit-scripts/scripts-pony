from decorator import decorator
from syslog import syslog,LOG_ERR,LOG_INFO
LOG_AUTHPRIV = 10<<3
import subprocess
import getpass, os

tag="Unknown"+getpass.getuser()

def set_tag(ctag,locker):
    """Sets the tag and usual locker this app is assoiciated with.

    This is used to label log entries, including whether this instance
    is running in an unusual locker."""

    global tag,unusual,user
    l = getpass.getuser()
    user = None
    if l == locker:
        tag = ctag
        unusual = False
    else:
        tag = "%s.%s" % (ctag,l)
        unusual = True
        if os.getuid() != os.getgid():
            # We're running out of a user locker
            user = l

def get_tag():
    return tag

def unusual_locker():
    return unusual

def err(mess,level=LOG_ERR):
    if user:
        zwrite(mess,recip=user,zsig=str(level))
    else:
        syslog(level|LOG_AUTHPRIV, ("%s: %s"%(tag,mess)).encode('utf-8'))
def info(mess):
    err(mess,level=LOG_INFO)

from webob.exc import HTTPException

class ExpectedException(Exception):
    pass

@decorator
def exceptions(func,*args,**kw):
    """Wrap a function such that it logs all exceptions (and reraises them)."""
    try:
        return func(*args,**kw)
    except HTTPException:
        raise
    except ExpectedException:
        raise
    except Exception as e:
        if not getattr(e,'already_syslogged',False):
            from .auth import current_user
            argness = ', '.join(repr(a) for a in args)
            if len(args) > 0 and len(kw) > 0:
                argness += ', '
            argness += ', '.join('%s=%s'%(k,repr(kw[k])) for k in kw)
            err("%s called %s(%s) but got: %s"
                % (current_user(),func.__name__,argness,e))
            e.already_syslogged = True
        raise

def zwrite(message,zclass="scripts",instance="",zsig="",recip=None):
    """Zephyr with the given message, class, instance suffix, and zsig."""
    if instance:
        instance = "%s:%s"%(tag.lower(),instance)
    else:
        instance = tag.lower()
    procness = ["/usr/bin/zwrite","-d"]
    if recip:
        procness += [recip]
    else:
        procness += ["-c",zclass.encode('utf-8'),
                     "-i",instance.encode('utf-8')]
    procness += ["-q",
                 "-s",zsig.encode('utf-8'),
                 "-m",message.encode('utf-8')]
    zwrite = subprocess.Popen(procness)
