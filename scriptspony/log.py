from syslog import syslog,LOG_ERR
LOG_AUTHPRIV = 10<<3

def err(mess):
    syslog(LOG_ERR|LOG_AUTHPRIV,mess)
def info(mess):
    syslog(LOG_AUTHPRIV,mess)
