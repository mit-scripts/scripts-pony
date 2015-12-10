#!/usr/bin/python

import site,os.path
site.addsitedir(os.path.dirname(__file__))

import transaction

from scriptspony.model import queue
from scriptspony import mail
from scripts import keytab, log, auth
from scriptspony.config.environment import load_environment

import email, sys, re
from email.header import make_header, decode_header
from email.utils import parseaddr

@log.exceptions
def handle_mail():
    
    message = email.message_from_file(sys.stdin)

    if keytab.exists():
        keytab.auth()

    if ('subject' not in message
        or 'delivered-to' not in message
        or 'from' not in message):
        return

    ID_PATTERN = re.compile(r'pony\+(\d+)\@')
    toname, to = parseaddr(unicode(make_header(decode_header(message['delivered-to']))))
    m = ID_PATTERN.search(to)
    if m is None:
        return
    id = int(m.group(1))

    byname, by = parseaddr(unicode(make_header(decode_header(message['from']))))
    by = by.lower()
    if by.endswith(u'@mit.edu'):
        by = by[:-len(u'@mit.edu')]

    t = queue.Ticket.get(id)

    RTID_PATTERN = re.compile(r'\[help.mit.edu\s+\#(\d+)\]')
    subject = unicode(make_header(decode_header(message['subject'])))
    m = RTID_PATTERN.search(subject)
    if m:
        if t.rtid is None:
            by = u'rt'
        t.rtid = int(m.group(1))
    
    newstate = t.state
    # TODO: blanche accounts-internal
    if by in (u'aswayze', u'jmorzins', u'othomas'):
        newstate = u'dns'
    body = u''
    for part in message.walk():
        if (part.get_content_maintype() == 'text'):
            body += unicode(part.get_payload(decode=True), part.get_content_charset('us-ascii'))
    t.addEvent(type=u'mail',state=newstate,by=by,target=u'us',
               subject=subject, body=body)

    transaction.commit()

if __name__ == '__main__':
    auth.set_user_from_parent_process()
    from paste.deploy import loadapp
    loadapp('config:development.ini',
            relative_to=os.path.dirname(__file__))
    handle_mail()
