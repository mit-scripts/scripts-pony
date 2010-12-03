import smtplib
from email.mime.text import MIMEText

from . import log

def sendmail(subject,body,fromaddr,toaddr,cc=None,rtcc=None,replyto=None):
    """Send mail."""

    if log.unusual_locker():
        subject = '[%s] %s' % (log.get_tag(),subject)
    
    msg = MIMEText(body)
    msg['From'] = fromaddr
    msg['Subject'] = subject
    msg['To'] = toaddr
    dests = [toaddr]
    if cc is not None:
        msg['CC'] = cc
        dests.append(cc)
    if rtcc is not None:
        msg['RT-Send-CC'] = rtcc
    if replyto is not None:
        msg['Reply-To'] = replyto
        
    s = smtplib.SMTP()
    s.connect()
    s.sendmail(fromaddr,dests,msg.as_string())
    s.quit()

def create_ticket(subject,body,rtcc,requestor):
    sendmail(subject,body,
             "%s@mit.edu" % requestor,
             "scripts@mit.edu",rtcc=rtcc)

def send_comment(subject,body,replyto,rtid,fromaddr,toaddr=None):
    if toaddr is not None:
        cc="scripts-comment@mit.edu"
    else:
        toaddr="scripts-comment@mit.edu"
        cc=None
    sendmail("%s [help.mit.edu #%s]" %(subject,rtid),body,
             "%s@mit.edu" % fromaddr,
             "%s@mit.edu" % toaddr,
             cc=cc,
             replyto="scripts-comment@mit.edu, %s"%(replyto))

def send_correspondence(subject,body,fromaddr,rtid):
    sendmail("%s [help.mit.edu #%s]" %(subject,rtid),body,
             "%s@mit.edu" % fromaddr,
             "scripts@mit.edu")
