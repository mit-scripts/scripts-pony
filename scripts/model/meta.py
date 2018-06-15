# -*- coding: utf-8 -*-
"""Models relating to tracking information on .mit.edu hostname requests."""

from sqlalchemy import Binary
from sqlalchemy.orm.exc import NoResultFound
import sqlalchemy.orm

sqlalchemy.orm.ScopedSession = sqlalchemy.orm.scoped_session
from elixir import Entity, Field, using_options, using_table_options, setup_all
import random, hmac, hashlib


def tname(typ):
    return typ.__name__.lower()


class Meta(Entity):
    using_options(tablename=tname)
    using_table_options(mysql_engine="InnoDB", mysql_charset="utf8")

    # Secret key
    secret = Field(Binary(8), required=True)

    def __init__(self):
        self.secret = "".join(chr(random.randint(0, 255)) for x in xrange(8))

    @staticmethod
    def token_for_user(user):
        return hmac.new(Meta.get().secret, user, hashlib.sha1).hexdigest()

    @staticmethod
    def get():
        try:
            return Meta.query.one()
        except NoResultFound:
            return Meta()


setup_all()
