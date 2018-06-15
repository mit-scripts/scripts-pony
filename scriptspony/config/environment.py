# -*- coding: utf-8 -*-
"""WSGI environment setup for ScriptsPony."""

import getpass,os

from scriptspony.config.app_cfg import base_config

__all__ = ['load_environment']

#Use base_config to setup the environment loader function
tg_load_environment = base_config.make_load_environment()

def load_environment(global_conf,app_conf):
    ## Hack to make our sqlalchemy config depend on scripts user
    url = ('mysql://sql.mit.edu/%s+scripts-pony?read_default_file=~/.my.cnf'
           % getpass.getuser())
    app_conf['sqlalchemy.url'] = url
    # Hack to make our mail recipient depend on scripts user
    global_conf['error_email_from'] = getpass.getuser()+'@scripts.mit.edu'
    if os.getuid() != os.getgid():
        global_conf['email_to'] = getpass.getuser()+'@mit.edu'
    #print "Overriding sqlalchemy.url to: %s" % url
    return tg_load_environment(global_conf,app_conf)


