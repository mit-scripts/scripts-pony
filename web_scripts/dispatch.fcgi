#!/usr/bin/env python

import os,sys

webappdir = os.path.realpath(os.path.dirname(os.path.abspath(__file__))+'/..')

import site
site.addsitedir(webappdir)

__requires__='ScriptsPony'
import pkg_resources
pkg_resources.require('ScriptsPony')

restart_file = __file__

from flup.server.fcgi import WSGIServer
import time
from os.path import getmtime

# Deploy it using FastCGI
if __name__ == '__main__':
    # from /mit/xavid/Public/bazki/lib/bazjunk/fcgi.py
    class RestartingServer(WSGIServer):
        """A variant on WSGIServer that exits if we've been modified, to
        allow Apache to restart us."""
        
        def __init__(self,app,file):
            WSGIServer.__init__(self,app)
            self.file = file
            self.starttime = time.time()
    
        def _mainloopPeriodic(self):
            WSGIServer._mainloopPeriodic(self)
        
            mod = getmtime(self.file)
            if mod > self.starttime:
                self._keepGoing = False
    try:
        # Load the WSGI application from the config file
        from paste.deploy import loadapp
        wsgi_app = loadapp('config:'+webappdir+'/development.ini')
        
        RestartingServer(wsgi_app,restart_file).run()
    except Exception,e:
        from traceback import format_exception
        import pwd,socket,sys,os
        tup = sys.exc_info()
        def errApp(environ, start_response):
            start_response('500 Flup Error', [('Content-Type', 'text/plain')],
                           tup)
            
            for l in format_exception(*tup):
                yield l
            whoami = pwd.getpwuid(os.getuid())[0]
            hostname = socket.gethostname()
            yield "To restart: touch %s" % restart_file
        RestartingServer(errApp,restart_file).run()
