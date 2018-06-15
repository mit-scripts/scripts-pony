# -*- coding: utf-8 -*-
"""Models relating to tracking information keyed on user."""

from sqlalchemy import *
from sqlalchemy.orm import mapper, relation
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Integer, Unicode, PickleType

# from sqlalchemy.orm import relation, backref

from scriptspony.model import DeclarativeBase, metadata, DBSession


class UserInfo(DeclarativeBase):
    __tablename__ = "user_info"

    def __init__(self, user=None):
        self.user = user
        self.lockers = []

    # Athena username
    user = Column(Unicode(255), primary_key=True)
    # List of lockers this person has used in the past
    lockers = Column(PickleType, default=[])
