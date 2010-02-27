#!/usr/bin/python

import site,os.path
site.addsitedir(os.path.dirname(__file__))

import transaction

from scriptspony.model import queue
from scriptspony import util,keytab,mail,log,auth,vhosts

@log.exceptions
def check_dns():
    if keytab.exists():
        keytab.auth()

    for t in queue.Ticket.query.filter_by(state=u'dns'):
        path = vhosts.get_path(t.locker,t.hostname)
        if util.points_at_scripts(t.hostname):
            subject = u"Hostname %s now working"%t.hostname
            body = u"""Hello,

Just wanted to let you know that the hostname %(hostname)s is now configured and working.  It currently points to /mit/%(locker)s/web_scripts/%(path)s.  Let us know if you run into any issues.

~The SIPB Scripts Team
http://scripts.mit.edu/

/set status=resolved
""" % dict(hostname=t.hostname,locker=t.locker,path=path)
            mail.send_correspondence(subject,body,t.id,rtid=t.rtid)        
            t.addEvent(type=u'mail',state=u'resolved',by=u'dns',
                       target=u'user',
                       subject=subject,
                       body=body)

    transaction.commit()

if __name__ == '__main__':
    auth.set_user_from_parent_process()
    from paste.deploy import loadapp
    loadapp('config:development.ini',
            relative_to=os.path.dirname(__file__))
    check_dns()
