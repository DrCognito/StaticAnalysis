from cache import Base
from cache.cache import CacheItem
from sqlalchemy import create_engine, Column, Integer, BigInteger, Float
from typing import List
from pandas import DataFrame, read_sql
from sqlalchemy.orm import Session


class PlayerPosIndex(CacheItem, Base):
    __tablename__ = "player_pos_index"
    steamID = Column(BigInteger, primary_key=True)


class PlayerPos(Base):
    __tablename__ = "player_pos"
    replayID = Column(Integer, primary_key=True)
    steamID = Column(BigInteger, primary_key=True)
    xCoordinate = Column(Float, primary_key=True)
    yCoordinate = Column(Float, primary_key=True)
    # An integer may be more logical but this is probably safer
    count = Column(Float)


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)


def is_cached(session: Session, replay_id: int, steam_id: int, version: int) -> bool:
    query = session.query(PlayerPosIndex).filter(PlayerPosIndex.replayID == replay_id,
                                                 PlayerPosIndex.steamID == steam_id)

    cache = query.one_or_none()
    if cache is not None:
        return cache.process_version == version
    else:
        return False


def get_dataframe(session: Session, replay_ids: List[int],
                  steam_id: int) -> DataFrame:
    query = session.query(PlayerPos)\
                   .filter(PlayerPos.replayID.in_(replay_ids),
                           PlayerPos.steamID == steam_id)
    sql_query = query.with_entities(PlayerPos.xCoordinate,
                                    PlayerPos.yCoordinate,
                                    PlayerPos.count).statement
    return read_sql(sql_query, session.bind)