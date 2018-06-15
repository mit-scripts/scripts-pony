# -*- coding: utf-8 -*-
"""Setup the ScriptsPony application"""
from __future__ import print_function

import logging

import transaction
from tg import config

from scriptspony.config.environment import load_environment

__all__ = ['setup_app']

log = logging.getLogger(__name__)


def setup_app(command, conf, vars):
    """Place any commands to setup scriptspony here"""
    load_environment(conf.global_conf, conf.local_conf)
    # Load the models
    from scriptspony import model
    print("Creating tables")
    #model.metadata.drop_all(bind=config['tg.app_globals'].sa_engine)
    model.metadata.create_all(bind=config['tg.app_globals'].sa_engine)

    transaction.commit()
    print("Successfully setup")
