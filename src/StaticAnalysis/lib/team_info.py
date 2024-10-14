from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, Integer,
                        String, and_, create_engine, or_)
from sqlalchemy.orm import reconstructor, relationship, declarative_base

import StaticAnalysis
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TeamSelections import TeamSelections

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
        path = StaticAnalysis.CONFIG['database']["TEAM_DB_PATH"]
    engine = create_engine(path, echo=False)
    Base_TI.metadata.create_all(engine)

    return engine


# Adapt team_db class
class TeamInfo(TeamInfo_DB):
    @reconstructor
    def __init__(self):
        self._filter = None
        self.extra_stackid = None
        self.extra_id_filter = None

    @property
    def filter(self):
        id_filter = Replay.teams.any(TeamSelections.teamID == self.team_id)
        if self.extra_id_filter is not None:
            id_filter = and_(self.extra_id_filter, id_filter)

        if self.extra_stackid is not None:
            stack_filter = Replay.teams.any(TeamSelections.stackID.in_(
                                            (self.stack_id, self.extra_stackid)))
        else:
            stack_filter = Replay.teams.any(TeamSelections.stackID ==
                                            self.stack_id)
        return or_(id_filter, stack_filter)

    def custom_filter(self, id_comp: Column, stack_comp: Column):
        """
        Returns a filter that compares id_comp to ids and stack_comp to stacks
        """
        id_filter = id_comp == self.team_id
        if self.extra_id_filter is not None:
            id_filter = and_(self.extra_id_filter, id_filter)

        if self.extra_stackid is not None:
            stack_filter = (stack_comp.in_(
                            (self.stack_id, self.extra_stackid)))
        else:
            stack_filter = stack_comp == self.stack_id
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
