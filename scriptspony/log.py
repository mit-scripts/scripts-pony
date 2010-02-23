from decorator import decorator
from syslog import syslog,LOG_ERR,LOG_INFO
LOG_AUTHPRIV = 10<<3
import getpass, subprocess
import tg

def err(mess,level=LOG_ERR):
    dotlocker = ".%s" % getpass.getuser()
    if dotlocker == ".pony":
        dotlocker = ''
    syslog(level|LOG_AUTHPRIV,"Pony%s: %s"%(dotlocker,mess))
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
    except Exception,e:
        if not getattr(e,'already_syslogged',False):
            from .auth import current_user
            argness = ', '.join(repr(a) for a in args)
            if len(args) > 0 and len(kw) > 0:
                argness += ', '
            argness += ', '.join('%s=%s'%(k,repr(kw[k])) for k in kw)
            err("%s called %s(%s) but got: %s"
                % (current_user(),func.func_name,argness,e))
            e.already_syslogged = True
        raise

def zwrite(message,id):
    """Zephyr about the given hostname with the given message."""
    dotlocker = ".%s" % getpass.getuser()
    if dotlocker == ".pony":
        dotlocker = ''
    zwrite = subprocess.Popen(["/usr/bin/zwrite","-d","-c","xavetest",
                               "-i","pony%s:%s"%(dotlocker,id),
                               "-s","%s%s"%(tg.request.host_url,
                                            tg.url('/ticket/%s'%id)),
                               "-m",message])
    
