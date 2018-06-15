# -*- coding: utf-8 -*-
"""
Global configuration file for TG2-specific settings in ScriptsPony.

This file complements development/deployment.ini.

Please note that **all the argument values are strings**. If you want to
convert them into boolean, for example, you should use the
:func:`paste.deploy.converters.asbool` function, as in::
    
    from paste.deploy.converters import asbool
    setting = asbool(global_conf.get('the_setting'))
 
"""

from tg.configuration import AppConfig

import scriptspony
from scriptspony import model
from scriptspony.lib import app_globals, helpers

from .. import vhosts

base_config = AppConfig()
base_config.renderers = []

base_config.package = scriptspony

# Set the default renderer
base_config.default_renderer = "mako"
base_config.renderers.append("mako")
# if you want raw speed and have installed chameleon.genshi
# you should try to use this renderer instead.
# warning: for the moment chameleon does not handle i18n translations
# base_config.renderers.append('chameleon_genshi')

# Configure the base SQLALchemy Setup
base_config.use_sqlalchemy = True
base_config.model = scriptspony.model
base_config.DBSession = scriptspony.model.DBSession

base_config.use_toscawidgets = False
