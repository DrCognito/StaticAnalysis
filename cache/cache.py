from sqlalchemy import Column, Integer, BigInteger, DateTime, Float
from sqlalchemy import create_engine, ForeignKey, or_
from sqlalchemy.types import Enum, Integer
# from sqlalchemy.ext.declarative import DeclarativeMeta, declared_attr
from cache import Base
import enum


class CacheType(enum):
    PLAYER_POS = 1


class CacheItem():

    replayID = Column(BigInteger, primary_key=True)
    # cache_type = Column(Enum(CacheType), primary_key=True)
    process_version = Column(Integer)
