# -*- coding: utf-8 -*-
"""The application's model objects"""
from __future__ import absolute_import

from scripts.model import DBSession, DeclarativeBase

__all__ = ["user", "queue", "meta"]

# Global metadata.
# The default metadata is the one from the declarative base.
metadata = DeclarativeBase.metadata

# If you have multiple databases with overlapping table names, you'll need a
# metadata for each database. Feel free to rename 'metadata2'.
# metadata2 = MetaData()

#####
# Generally you will not want to define your table's mappers, and data objects
# here in __init__ but will want to create modules them in the model directory
# and import them at the bottom of this file.
#
######


def init_model(engine):
    """Call me before using any of the tables or classes in the model."""

    DBSession.configure(bind=engine)
    # If you are using reflection to introspect your database and create
    # table objects for you, your tables must be defined and mapped inside
    # the init_model function, so that the engine is available if you
    # use the model outside tg2, you need to make sure this is called before
    # you use the model.

    #
    # See the following example:

    # global t_reflected

    # t_reflected = Table("Reflected", metadata,
    #    autoload=True, autoload_with=engine)

    # mapper(Reflected, t_reflected)


# Import your model modules here.
from . import user
from . import queue
from scripts.model import meta
