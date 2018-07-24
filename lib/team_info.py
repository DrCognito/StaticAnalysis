from collections import OrderedDict
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Replay import Replay
from replays.TeamSelections import TeamSelections
from sqlalchemy import or_

from datetime import datetime, timedelta
from os import environ as environment

from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, Integer,
                        String, create_engine)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship


Base_TI = declarative_base()


class TeamInfo_DB(Base_TI):
    __tablename__ = "team_info"
    team_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    last_change = Column(DateTime)
    stack_id = Column(String)

    players = relationship("TeamPlayer")


class TeamPlayer(Base_TI):
    __tablename__ = "team_players"
    player_id = Column(BigInteger, primary_key=True)
    team_id = Column(Integer, ForeignKey(TeamInfo_DB.team_id),
                     primary_key=True)
    name = Column(String)


def InitTeamDB(path=None):
    if path is None:
        path = environment["TEAM_DB_PATH"]
    engine = create_engine(path, echo=False)
    Base_TI.metadata.create_all(engine)

    return engine


# Adapt team_db class
class TeamInfo(TeamInfo_DB):
    def __init__(self):
        print("constructor!")
        self._filter = None

    @property
    def filter(self):
        id_filter = Replay.teams.any(TeamSelections.teamID == self.team_id)
        stack_filter = Replay.teams.any(TeamSelections.stackID == self.stack_id)
        return or_(id_filter, stack_filter)

    def replay_count(self, session):
        return session.query(Replay).filter(self.filter).count()

    def get_replays(self, session, additional_filter=None):
        if additional_filter is None:
            return session.query(Replay).filter(self.filter)
        else:
            return session.query(Replay).filter(self.filter)\
                                        .filter(additional_filter)


# Teams = {}
# InitTeamDB()
# TeamIDs = {}
# PlayerIDs = {}

# PlayerIDs['Mad Lads'] = OrderedDict()
# PlayerIDs['Mad Lads']['Qojkva'] = 76561198047004422
# PlayerIDs['Mad Lads']['Madara'] = 76561198055695796
# PlayerIDs['Mad Lads']['Khezu'] = 76561198129291346
# PlayerIDs['Mad Lads']['MaybeNextTime'] = 76561198047219142
# PlayerIDs['Mad Lads']['Synderen'] = 76561197964547457
# TeamIDs['Mad Lads'] = 5229049
# Teams['Mad Lads'] = TeamInfo(name='Mad Lads', players=PlayerIDs['Mad Lads'],
#                              team_id=TeamIDs['Mad Lads'])
