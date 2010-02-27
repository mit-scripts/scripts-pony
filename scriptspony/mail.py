import getpass
import smtplib
from email.mime.text import MIMEText

def sendmail(subject,body,fromaddr,toaddr,cc=None,rtcc=None,replyto=None):
    """Send mail."""

    uslocker = getpass.getuser()
    if uslocker != 'pony':
        subject = '[Pony.%s] %s' % (uslocker,subject)
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = fromaddr
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

def ponyaddr(id):
    lockerdot = "%s." % getpass.getuser()
    if lockerdot == "pony.":
        lockerdot = ''    
    return "pony+%s@%sscripts.mit.edu" % (id,lockerdot)

def create_ticket(subject,body,id,requestor):
    sendmail(subject,body,
             "%s@mit.edu" % requestor,
             "scripts@mit.edu",rtcc=ponyaddr(id))

def send_comment(subject,body,id,rtid,to):
    sendmail("%s [help.mit.edu #%s]" %(subject,rtid),body,
             ponyaddr(id),
             "%s@mit.edu" % to,
             cc="scripts-comment@mit.edu",
             replyto="scripts-comment@mit.edu, %s"%(ponyaddr(id)))

def send_correspondence(subject,body,id,rtid):
    sendmail("%s [help.mit.edu #%s]" %(subject,rtid),body,
             ponyaddr(id),
             "scripts@mit.edu")
