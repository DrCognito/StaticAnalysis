from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, Integer,
                        String, and_, create_engine, or_)
from sqlalchemy.orm import reconstructor, relationship, declarative_base, Session

import StaticAnalysis
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TeamSelections import TeamSelections
from herotools.util import convert_to_64_bit

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

    @staticmethod
    def get_team_name(team_id: int, team_session: Session = None):
        if team_session is None:
            team_session = StaticAnalysis.team_session
        t = team_session.query(TeamInfo).filter(TeamInfo.team_id == team_id).one_or_none()
        if t is None:
            raise ValueError(f"No such team id {team_id} exists in DB.")
        
        return t.name


def get_player(player_id: int, team_session: Session = None):
    player_id = convert_to_64_bit(player_id)
    if team_session is None:
        team_session = StaticAnalysis.team_session
    return team_session.query(TeamPlayer).filter(TeamPlayer.player_id == player_id).one_or_none()


def get_players(players: list['Player | int'], team_session: Session = None) -> list[TeamPlayer]:
    from StaticAnalysis.replays.Player import Player
    if team_session is None:
        team_session = StaticAnalysis.team_session
    output: list[TeamPlayer] = []
    for p in players:
        if type(p) is int:
            p = convert_to_64_bit(p)
            db_p = team_session.query(TeamPlayer).filter(TeamPlayer.player_id == p).one_or_none()
            output.append(db_p)
        if type(p) is Player:
            db_p = team_session.query(TeamPlayer).filter(TeamPlayer.player_id == p.steamID).one_or_none()
            output.append(db_p)
        else:
            raise ValueError(f'Invalid type {type(p)} in player list argument.')
    return output


def get_player_teams(players: list['Player | int'], team_session: Session = None):
    from StaticAnalysis.replays.Player import Player
    team_players = get_players(players, team_session)
    teams = []
    for p in team_players:
        if p is not None:
            t = team_session.query(TeamInfo).filter(TeamInfo.team_id == p.team_id).one_or_none()
        else:
            t = None
        teams.append(t)
        
    return teams