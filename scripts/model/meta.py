# -*- coding: utf-8 -*-
"""Models relating to tracking information on .mit.edu hostname requests."""

from sqlalchemy import Binary, Column, Integer
from sqlalchemy.orm.exc import NoResultFound

import random, hmac, hashlib

from . import DBSession, DeclarativeBase


class Meta(DeclarativeBase):
    __tablename__ = "meta"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8"}

    id = Column(Integer, primary_key=True)

    # Secret key
    secret = Column(Binary(8), nullable=False)

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
            meta = Meta()
            DBSession.add(meta)
            return meta
