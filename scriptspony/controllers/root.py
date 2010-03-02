# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _, lazy_ugettext as l_
import pylons

from scriptspony.lib.base import BaseController
from scriptspony.model import DBSession, metadata
from scriptspony.model.user import UserInfo
from scriptspony.controllers.error import ErrorController

from sqlalchemy.orm.exc import NoResultFound

from decorator import decorator

from .. import auth,vhosts,mail
from ..model import queue

__all__ = ['RootController']

# Not in auth because it depends on TG
@decorator
def scripts_team_only(func,*args,**kw):
    if not auth.on_scripts_team():
        flash("You are not authorized for this area!")
        redirect('/')
    else:
        return func(*args,**kw)

class RootController(BaseController):
    """
    The root controller for the ScriptsPony application.
    
    All the other controllers and WSGI applications should be mounted on this
    controller. For example::
    
        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()
    
    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.
    
    """
    
    error = ErrorController()

    @expose('scriptspony.templates.index')
    def index(self,locker=None):
        """Handle the front-page."""
        if locker is not None and pylons.request.response_ext:
            locker += pylons.request.response_ext
        
        olocker = locker
        hosts = None
        user = auth.current_user()
        https = auth.is_https()
        # Find or create the associated user info object.
        # TODO: is there a find_or_create sqlalchemy method?
        if user:
            try:
                user_info = DBSession.query(UserInfo).filter(UserInfo.user==user).one()
            except NoResultFound:
                user_info = UserInfo(user)
                DBSession.add(user_info)
        else:
            user_info = None

        if user is not None:
            if locker is None:
                locker = user
            try:
                hosts = vhosts.list_vhosts(locker)
                hosts.sort(key=lambda k:k[0])
            except auth.AuthError,e:
                flash(e.message)
                # User has been deauthorized from this locker
                if locker in user_info.lockers:
                    user_info.lockers.remove(locker)
                    DBSession.add(user_info)
                if olocker is not None:
                    return self.index()
                else:
                    return dict(hosts={},locker=locker,user_info=user_info)
            else:
                # Append locker to the list in user_info if it's not there
                if not locker in user_info.lockers:
                    user_info.lockers.append(locker)
                    user_info.lockers.sort()
                    DBSession.add(user_info)
                    flash('You can administer the "%s" locker.' % locker)
        return dict(hosts=hosts, locker=locker, user_info=user_info,
                    https=https)

    @expose('scriptspony.templates.edit')
    def edit(self,locker,hostname,path=None,token=None):
        if path is None and pylons.request.response_ext:
            hostname += pylons.request.response_ext
        if vhosts.is_host_reified(hostname):
            flash("The host '%s' has special configuration; email scripts@mit.edu to make changes to it." % hostname)
            redirect('/index/'+locker)
        if path is not None:
            if token != auth.token():
                flash("Invalid token!")
            else:
                try:
                    vhosts.set_path(locker,hostname,path)
                except vhosts.UserError,e:
                    flash(e.message)
                else:
                    flash("Host '%s' reconfigured."%hostname)
                    redirect('/index/'+locker)
        else:
            try:
                path=vhosts.get_path(locker,hostname)
            except vhosts.UserError,e:
                flash(e.message)
                redirect('/index/'+locker)
        return dict(locker=locker, hostname=hostname,
                    path=path)

    @expose('scriptspony.templates.new')
    def new(self,locker,hostname='',path='',token=None):
        if not hostname and not path and pylons.request.response_ext:
            locker += pylons.request.response_ext
        if hostname:
            if token != auth.token():
                flash("Invalid token!")
            else:
                try:
                    status = vhosts.request_vhost(locker,hostname,path)
                except vhosts.UserError,e:
                    flash(e.message)
                else:
                    flash(status)
                    redirect('/index/'+locker)
        else:
            try:
                auth.validate_locker(locker)
            except auth.AuthError,e:
                flash(e.message)
                redirect('/')

        return dict(locker=locker,hostname=hostname,path=path)

    @expose('scriptspony.templates.queue')
    @scripts_team_only
    def queue(self,**kw):
        all = ('open','moira','dns','resolved')
        if len(kw) <= 0:
            kw = dict(open='1',moira='1',dns='1')
        query = queue.Ticket.query
        for k in all:
            if k not in kw:
                query = query.filter(queue.Ticket.state != k)
        return dict(tickets=query.all(),all=all,included=kw)

    @expose('scriptspony.templates.ticket')
    @scripts_team_only
    def ticket(self,id):
        return dict(tickets=[queue.Ticket.get(int(id))])

    @expose('scriptspony.templates.message')
    @scripts_team_only
    def approve(self,id,subject=None,body=None,token=None):
        t = queue.Ticket.get(int(id))
        if t.state != 'open':
            flash("This ticket's not open!")
            redirect('/ticket/%s'%id)
        if t.rtid is None:
            flash("This ticket has no RT ID!")
            redirect('/ticket/%s'%id)
        if subject and body:
            if token != auth.token():
                flash("Invalid token!")
            else:
                try:
                    vhosts.actually_create_vhost(t.locker,t.hostname,t.path)
                except vhosts.UserError,e:
                    flash(e.message)
                else:
                    # Send mail and records it as an event
                    mail.send_comment(subject,body,t.id,t.rtid,
                                      auth.current_user(),'jweiss')
                    t.addEvent(type='mail',state='moira',target='jweiss',
                               subject=subject,body=body)
                    redirect('/queue')
        short = t.hostname[:-len('.mit.edu')]
        return dict(tickets=[t],action=url('/approve/%s'%id),
                    subject="scripts-vhosts CNAME request: %s"%short,
                    body="""Hi Jonathon,

At your convenience, please make %(short)s an alias of scripts-vhosts.

stella scripts-vhosts -a %(short)s

Thanks!
-%(first)s

/set status=stalled
""" % dict(short=short,first=auth.first_name()))
            
