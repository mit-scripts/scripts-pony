from decorator import decorator
from syslog import syslog,LOG_ERR,LOG_INFO
LOG_AUTHPRIV = 10<<3

def err(mess):
    syslog(LOG_ERR|LOG_AUTHPRIV,mess)
def info(mess):
    syslog(LOG_INFO|LOG_AUTHPRIV,mess)

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
        from .auth import current_user
        argness = ', '.join(repr(a) for a in args)
        if len(args) > 0 and len(kw) > 0:
            argness += ', '
        argness += ', '.join('%s=%s'%(k,repr(kw[k])) for k in kw)
        err("%s called %s(%s) but got: %s"
            % (current_user(),func.func_name,argness,e))
        raise
