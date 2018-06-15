# -*- coding: utf-8 -*-
"""Models relating to tracking information keyed on user."""

from sqlalchemy import Column
from sqlalchemy.types import Unicode, PickleType

# from sqlalchemy.orm import relation, backref

from scriptspony.model import DeclarativeBase


class UserInfo(DeclarativeBase):
    __tablename__ = "user_info"

    def __init__(self, user=None):
        self.user = user
        self.lockers = []

    # Athena username
    user = Column(Unicode(255), primary_key=True)
    # List of lockers this person has used in the past
    lockers = Column(PickleType, default=[])
