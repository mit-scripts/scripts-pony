#!/usr/bin/env python

import os.path

import transaction

from scriptspony.model import queue
from scripts import keytab, log, auth

import email, sys, re
from email.header import make_header, decode_header
from email.utils import parseaddr


@log.exceptions
def handle_mail():

    message = email.message_from_file(sys.stdin)

    if keytab.exists():
        keytab.auth()

    if (
        "subject" not in message
        or "delivered-to" not in message
        or "from" not in message
    ):
        return

    ID_PATTERN = re.compile(r"pony\+(\d+)\@")
    toname, to = parseaddr(unicode(make_header(decode_header(message["delivered-to"]))))
    m = ID_PATTERN.search(to)
    if m is None:
        t = None
    else:
        t = queue.Ticket.get(int(m.group(1)))

    byname, by = parseaddr(unicode(make_header(decode_header(message["from"]))))
    by = by.lower()
    if by.endswith(u"@mit.edu"):
        by = by[: -len(u"@mit.edu")]

    RTID_PATTERN = re.compile(r"\[help.mit.edu\s+\#(\d+)\]")
    subject = unicode(make_header(decode_header(message["subject"])))
    m = RTID_PATTERN.search(subject)
    if m:
        rtid = int(m.group(1))
        if t is None:
            t = queue.Ticket.query.filter_by(rtid=rtid).one()
        else:
            if t.rtid is None:
                by = u"rt"
            t.rtid = rtid

    newstate = t.state
    # TODO: blanche accounts-internal
    if by in (
        u"aswayze",
        u"bowser",
        u"jtravers",
        u"kwitt",
        u"mannys",
        u"mwollman",
        u"ovidio",
        u"thorn",
    ):
        newstate = u"dns"
    body = u""
    for part in message.walk():
        if part.get_content_maintype() == "text":
            body += unicode(
                part.get_payload(decode=True), part.get_content_charset("us-ascii")
            )
    t.addEvent(
        type=u"mail", state=newstate, by=by, target=u"us", subject=subject, body=body
    )

    transaction.commit()


if __name__ == "__main__":
    auth.set_user_from_parent_process()
    from paste.deploy import loadapp

    loadapp("config:development.ini", relative_to=os.path.dirname(__file__))
    handle_mail()
