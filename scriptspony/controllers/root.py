# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _, lazy_ugettext as l_

from scriptspony.lib.base import BaseController
from scriptspony.model import DBSession, metadata
from scriptspony.controllers.error import ErrorController

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
        hosts = None
        user = auth.current_user()
        if user is not None:
            if locker is None:
                locker = user
            try:
                hosts = vhosts.list_vhosts(locker)
                hosts.sort(key=lambda k:k[0])
            except auth.AuthError:
                flash("You do not have permission to administer the '%s' locker."%locker)
                return self.index()
        return dict(hosts=hosts, locker=locker)

    @expose('scriptspony.templates.edit')
    def edit(self,locker,hostname,path=None):
        if path is not None:
            try:
                message = vhosts.set_path(locker,hostname,path)
            except vhosts.UserError,e:
                flash(e.message)
            else:
                flash(message)
                redirect('/index/'+locker)
        else:
            path=vhosts.get_path(locker,hostname)
        return dict(locker=locker, hostname=hostname,
                    path=path)

    @expose('scriptspony.templates.new')
    def new(self,locker,hostname='',path=''):
        if hostname:
            try:
                vhosts.request_vhost(locker,hostname,path)
            except vhosts.UserError,e:
                flash(e.message)
        return dict(locker=locker,hostname=hostname,path=path)
