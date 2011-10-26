# -*- coding: utf-8 -*-
"""Models relating to tracking information on .mit.edu hostname requests."""

from sqlalchemy import *
from elixir import (ManyToOne, Entity, Field, OneToMany,
                    using_options, using_table_options,
                    ManyToMany, setup_all,
                    drop_all, create_all, session)
import datetime

import tg

from scripts import auth,log

def tname(typ):
    return typ.__name__.lower()

class Ticket(Entity):
    using_options(tablename=tname)
    using_table_options(mysql_engine='InnoDB',mysql_charset='utf8')

    # Athena username
    requestor = Field(Unicode(255), index=True)
    # Locker name
    locker = Field(Unicode(255), index=True)
    # Hostname involved
    hostname = Field(Unicode(255), index=True)
    # path
    path = Field(Unicode(255))
    # "open" or "moira" or "dns" or "resolved"
    state = Field(Unicode(32))
    rtid = Field(Integer)
    # Purpose
    purpose = Field(UnicodeText())
    
    events = OneToMany('Event',order_by='timestamp')

    @staticmethod
    def create(locker,hostname,path,requestor=None,purpose=""):
        if requestor is None:
            requestor = auth.current_user()
        t = Ticket(requestor=requestor,
                   hostname=hostname,locker=locker,path=path,
                   state="open",purpose=purpose)
        session.flush()
        t.addEvent(type='request',state="open",target='us')
        return t

    def addEvent(self,type,state,by=None,target=None,subject=None,body=None):
        if by is None:
            by = auth.current_user()
        Event(ticket=self,type=type,target=target,subject=subject,body=body,
              by=by)
        if state != self.state:
            self.state = state
            pat = "%s's %s changed the ticket re: %s to %s"
        else:
            pat = "%s's %s left the ticket re: %s as %s"
        try:
            url = "%s%s"%(tg.request.host_url, tg.url('/queue'))
        except:
            # Default to something sane if we're not in the context of a request
            url = "https://pony.scripts.mit.edu:444/queue"

        log.zwrite(pat % (by,type,self.hostname,state),
                   instance=self.id,zsig=url)
    
    @staticmethod
    def all():
        return Ticket.query.all()

class Event(Entity):
    using_options(tablename=tname)
    using_table_options(mysql_engine='InnoDB',mysql_charset='utf8')

    ticket = ManyToOne('Ticket',required=True)
    # 'mail' or 'dns' or 'request'
    type = Field(Unicode(32))
    # 'jweiss' or 'us' or 'user'
    target = Field(Unicode(32))
    by = Field(Unicode(255))
    timestamp = Field(DateTime, default=datetime.datetime.now)
    subject = Field(UnicodeText())
    body = Field(UnicodeText())

setup_all()
