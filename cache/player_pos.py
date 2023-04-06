from cache import Base
from cache.cache import CacheItem
from sqlalchemy import create_engine, Column, Integer, BigInteger, Float
from typing import List
from pandas import DataFrame, read_sql
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


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


def get_cache_dataframe(session: Session, replay_ids: List[int],
                  steam_id: int) -> DataFrame:
    query = session.query(PlayerPos)\
                   .filter(PlayerPos.replayID.in_(replay_ids),
                           PlayerPos.steamID == steam_id)
    sql_query = query.with_entities(PlayerPos.xCoordinate,
                                    PlayerPos.yCoordinate,
                                    PlayerPos.count).statement
    return read_sql(sql_query, session.bind)


def delete_pos_cache(session: Session, replay_id: int, steam_id: int):
    try:
        query = session.query(PlayerPos.steamID == steam_id, PlayerPos.replayID == replay_id)
        query.delete()

        query = session.query(PlayerPosIndex.steamID == steam_id, PlayerPosIndex.replayID == replay_id)
        query.delete()

        session.commit()
    except SQLAlchemyError as e:
        print(e)
        print(f"Failed to delete cache for {steam_id} in {replay_id}")
        session.rollback()
        exit(2)


def add_cache(session: Session, df: DataFrame, replay_id: int, steam_id: int, version: int):
    # Clear first in case we have an old version.
    delete_pos_cache(session, replay_id, steam_id)
    try:
        for _, row in df.iterrows():
            new_pos = PlayerPos()
            new_pos.replayID = replay_id
            new_pos.steamID = steam_id
            new_pos.xCoordinate = row['xCoordinate']
            new_pos.yCoordinate = row['yCoordinate']
            new_pos.count = row['count']

            session.add(new_pos)

        new_index = PlayerPosIndex()
        new_index.replayID = replay_id
        new_index.steamID = steam_id
        new_index.process_version = version

        session.add(new_index)
        session.commit()
    except SQLAlchemyError as e:
        print(e)
        print(f"Failed to cache pos for {steam_id} in {replay_id}")
        session.rollback()
        exit(2)

