#!/usr/bin/python

import site,os.path
site.addsitedir(os.path.dirname(__file__))

import transaction

from scriptspony.model import queue
from scriptspony import mail
from scripts import keytab, log, auth
from scriptspony.config.environment import load_environment

import email, sys, re

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
    m = ID_PATTERN.search(message['delivered-to'])
    if m is None:
        return
    id = int(m.group(1))

    by = unicode(message['from'].lower(),'utf-8',errors='replace')
    FROM_PATTERN = re.compile(r'\<([^<>]+)\>')
    m = FROM_PATTERN.search(by)
    if m:
        by = m.group(1)
    if by.endswith(u'@mit.edu'):
        by = by[:-len(u'@mit.edu')]

    t = queue.Ticket.get(id)

    RTID_PATTERN = re.compile(r'\[help.mit.edu\s+\#(\d+)\]')
    m = RTID_PATTERN.search(message['subject'])
    if m:
        if t.rtid is None:
            by = u'rt'
        t.rtid = int(m.group(1))
    
    newstate = t.state
    # TODO: blanche accounts-internal
    if by in (u'boojum', u'jdreed', u'jmorzins', u'mvan', u'othomas', u'peloquin'):
        newstate = u'dns'
    body = ''
    for part in message.walk():
        if (part.get_content_maintype() == 'text'):
            body += part.get_payload()
    t.addEvent(type=u'mail',state=newstate,by=by,target=u'us',
               subject=unicode(message['subject'],'utf-8',errors='replace'),
               body=unicode(body,'utf-8',errors='replace'))

    transaction.commit()

if __name__ == '__main__':
    auth.set_user_from_parent_process()
    from paste.deploy import loadapp
    loadapp('config:development.ini',
            relative_to=os.path.dirname(__file__))
    handle_mail()
