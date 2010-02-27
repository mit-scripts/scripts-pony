# -*- coding: utf-8 -*-
"""WSGI middleware initialization for the ScriptsPony application."""

from paste.pony import PonyMiddleware

from scriptspony.config.app_cfg import base_config
from scriptspony.config.environment import load_environment


__all__ = ['make_app']

# Use base_config to setup the necessary PasteDeploy application factory. 
# make_base_app will wrap the TG2 app with all the middleware it needs. 
make_base_app = base_config.setup_tg_wsgi_app(load_environment)

# from /mit/xavid/Public/bazki/lib/bazjunk/middleware/rewrite.py
class UnrewriteMiddleware(object):
    """Rewrite our URL back into the logical URL.

    Undoes the effects of a mod_rewrite so that URLs we
    generate look good.  Takes an app to wrap and a dict like:

    {'dispatch.fcgi':'','dispatch.cgi':'dev'}"""
    
    def __init__(self, app, substs):
        self.app = app
        self.substs = substs
        
    def __call__(self, environ, start_response):
        comps = environ['SCRIPT_NAME'].split('/')
        for act in self.substs:
            if act in comps:
                ind = comps.index(act)
                if self.substs[act]:
                    comps[ind] = self.substs[act]
                else:
                    del comps[ind]
        environ['SCRIPT_NAME'] = '/'.join(comps)
        return self.app(environ, start_response)

from ..auth import ScriptsAuthMiddleware

def make_app(global_conf, full_stack=True, **app_conf):
    """
    Set ScriptsPony up with the settings found in the PasteDeploy configuration
    file used.
    
    :param global_conf: The global settings for ScriptsPony (those
        defined under the ``[DEFAULT]`` section).
    :type global_conf: dict
    :param full_stack: Should the whole TG2 stack be set up?
    :type full_stack: str or bool
    :return: The ScriptsPony application with all the relevant middleware
        loaded.
    
    This is the PasteDeploy factory for the ScriptsPony application.
    
    ``app_conf`` contains all the application-specific settings (those defined
    under ``[app:main]``.
    
   
    """
    app = make_base_app(global_conf, full_stack=True, **app_conf)
    
    # Wrap your base TurboGears 2 application with custom middleware here
    app = PonyMiddleware(app)

    app = UnrewriteMiddleware(app,{'dispatch.fcgi':''})

    app = ScriptsAuthMiddleware(app)
    
    return app
