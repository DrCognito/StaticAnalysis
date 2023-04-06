from sqlalchemy import Column, Integer, BigInteger, DateTime, Float
from sqlalchemy import create_engine, ForeignKey, or_
from sqlalchemy.types import Enum, Integer
# from sqlalchemy.ext.declarative import DeclarativeMeta, declared_attr
from cache import Base
import enum
from pathlib import Path
from . import player_pos


class CacheItem():

    replayID = Column(BigInteger, primary_key=True)
    # cache_type = Column(Enum(CacheType), primary_key=True)
    process_version = Column(Integer)


def InitCacheDB(path: str):
    player_pos.InitDB(path)
