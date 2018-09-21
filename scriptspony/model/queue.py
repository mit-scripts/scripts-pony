# -*- coding: utf-8 -*-
"""Models relating to tracking information on .mit.edu hostname requests."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.orm import relationship
import datetime

import tg

from scripts import auth, log
from scriptspony.model import DBSession, DeclarativeBase


class Ticket(DeclarativeBase):
    __tablename__ = "ticket"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8"}

    id = Column(Integer, primary_key=True)
    # Athena username
    requestor = Column(Unicode(255), index=True)
    # Locker name
    locker = Column(Unicode(255), index=True)
    # Hostname involved
    hostname = Column(Unicode(255), index=True)
    # path
    path = Column(Unicode(255))
    # "open" or "moira" or "dns" or "resolved"
    state = Column(Unicode(32))
    rtid = Column(Integer)
    # Purpose
    purpose = Column(UnicodeText())

    events = relationship("Event", order_by="Event.timestamp", back_populates="ticket")

    @staticmethod
    def create(locker, hostname, path, requestor=None, purpose=""):
        if requestor is None:
            requestor = auth.current_user()
        t = Ticket(
            requestor=requestor,
            hostname=hostname,
            locker=locker,
            path=path,
            state="open",
            purpose=purpose,
        )
        DBSession.add(t)
        DBSession.flush()
        t.addEvent(type="request", state="open", target="us")
        return t

    def addEvent(self, type, state, by=None, target=None, subject=None, body=None):
        if by is None:
            by = auth.current_user()
        event = Event(
            ticket=self, type=type, target=target, subject=subject, body=body, by=by
        )
        DBSession.add(event)
        if state != self.state:
            self.state = state
            pat = "%s's %s changed the ticket re: %s to %s"
        else:
            pat = "%s's %s left the ticket re: %s as %s"
        try:
            url = "%s%s" % (tg.request.host_url, tg.url("/queue"))
        except:
            # Default to something sane if we're not in the context of a request
            url = "https://pony.scripts.mit.edu:444/queue"

        log.zwrite(pat % (by, type, self.hostname, state), instance=self.id, zsig=url)

    @staticmethod
    def all():
        return Ticket.query.all()


class Event(DeclarativeBase):
    __tablename__ = "event"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8"}

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("ticket.id"), nullable=False)
    ticket = relationship("Ticket", back_populates="events")
    # 'mail' or 'dns' or 'request'
    type = Column(Unicode(32))
    # 'accounts-internal' or 'us' or 'user'
    target = Column(Unicode(32))
    by = Column(Unicode(255))
    timestamp = Column(DateTime, default=datetime.datetime.now)
    subject = Column(UnicodeText())
    body = Column(UnicodeText())
