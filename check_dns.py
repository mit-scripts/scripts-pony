#!/usr/bin/python

import site,os.path
site.addsitedir(os.path.dirname(__file__))

from scriptspony.model import queue
from scriptspony import util,keytab,mail,log

@log.exceptions
def check_dns():
    if keytab.exists():
        keytab.auth()

    for t in queue.Ticket.get_by(state=dns):
        if util.points_at_scripts(t.hostname):
            subject = "Hostname %s now working"%t.hostname
            body = """Hello,

Just wanted to let you know that the hostname %(hostname)s is now configured and working.  It currently points to /mit/%(locker)s/web_scripts%(path)s.  Let us know if you run into any issues.

~The SIPB Scripts Team
http://scripts.mit.edu/

/set status=resolved
""" % dict(hostname=t.hostname,locker=locker,path=path))
            mail.send_correspondence(subject,body,t.id,rtid=t.rtid)        
            t.addEvent(type='mail',state='resolved',by='dns',
                       target='user',
                       subject=subject,
                       body=body)

if __name__ == '__main__':
    check_dns()
