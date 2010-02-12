# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _, lazy_ugettext as l_

from scriptspony.lib.base import BaseController
from scriptspony.model import DBSession, metadata
from scriptspony.model.user import UserInfo
from scriptspony.controllers.error import ErrorController

from sqlalchemy.orm.exc import NoResultFound

from .. import auth,vhosts

__all__ = ['RootController']


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
    def edit(self,locker,hostname,path=None):
        if vhosts.is_host_reified(hostname):
            flash("The host '%s' has special configuration; email scripts@mit.edu to make changes to it." % hostname)
            redirect('/index/'+locker)
        if path is not None:
            try:
                vhosts.set_path(locker,hostname,path)
            except vhosts.UserError,e:
                flash(e.message)
            else:
                flash("Host '%s' reconfigured."%hostname)
                redirect('/index/'+locker)
        else:
            path=vhosts.get_path(locker,hostname)
        return dict(locker=locker, hostname=hostname,
                    path=path)

    @expose('scriptspony.templates.new')
    def new(self,locker,hostname='',path=''):
        if hostname:
            try:
                status = vhosts.request_vhost(locker,hostname,path)
            except vhosts.UserError,e:
                flash(e.message)
            else:
                flash(status)
                redirect('/index/'+locker)

        return dict(locker=locker,hostname=hostname,path=path)
