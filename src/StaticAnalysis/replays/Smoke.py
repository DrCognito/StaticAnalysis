from sqlalchemy import (BigInteger, Column, Float, ForeignKey, Integer,
                        create_engine)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select
from sqlalchemy.types import Enum
from StaticAnalysis.lib.Common import average_coorinates
from StaticAnalysis.replays import Base
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.JSONProcess import get_smoke_summary
from StaticAnalysis.replays.Player import Player


class Smoke(Base):
    __tablename__ = "smokes"

    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    id = Column(Integer, primary_key=True)
    team = Column(Enum(Team), primary_key=True)

    startTime = Column(Integer)

    @hybrid_property
    def game_start_time(self):
        return self.startTime - self.replay.creepSpawn

    @game_start_time.expression
    def game_start_time(self):
        from .Replay import Replay
        creepSpawn = select(Replay.creepSpawn).\
            where(self.replayID == Replay.replayID).scalar_subquery()
        return self.startTime - creepSpawn

    endTime = Column(Integer)

    @hybrid_property
    def game_end_time(self):
        return self.endTime - self.replay.creepSpawn

    @game_end_time.expression
    def game_end_time(self):
        from .Replay import Replay
        creepSpawn = select(Replay.creepSpawn).\
            where(self.replayID == Replay.replayID).scalar_subquery()
        return self.endTime - creepSpawn

    averageXCoordinateStart = Column(Float)
    averageXCoordinateEnd = Column(Float)
    averageYCoordinateStart = Column(Float)
    averageYCoordinateEnd = Column(Float)

    # Relationships
    players_smoked = relationship("SmokedPlayers", back_populates="smoke",
                                  lazy="dynamic", primaryjoin=
                                  '''and_(SmokedPlayers.replayID == Smoke.replayID,
                                     SmokedPlayers.id == Smoke.id,
                                     SmokedPlayers.team == Smoke.team)''',
                                  cascade="all, delete-orphan")
    replay = relationship("Replay", back_populates="smoke_summary")

    def __init__(self, replay_in):
        self.replay = replay_in
        self.replayID = replay_in.replayID


class SmokedPlayers(Base):
    __tablename__ = "smokedplayers"

    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    id = Column(Integer, ForeignKey(Smoke.id), primary_key=True)
    team = Column(Enum(Team), ForeignKey(Smoke.team))
    steam_id = Column(BigInteger, ForeignKey(Player.steamID), primary_key=True)

    # Relationships
    smoke = relationship(Smoke, back_populates="players_smoked", primaryjoin=
                         '''and_(SmokedPlayers.replayID == Smoke.replayID,
                            SmokedPlayers.id == Smoke.id,
                            SmokedPlayers.team == Smoke.team)''')
    player = relationship(Player, lazy="select", primaryjoin=
                          '''and_(SmokedPlayers.steam_id == Player.steamID,
                          SmokedPlayers.replayID == Player.replayID)''')

    def __init__(self, smoke_in):
        self.replayID = smoke_in.replayID
        self.id = smoke_in.id

    def get_position_at(self, time, relative_to_match_time=True):
        return self.player.get_position_at(time, relative_to_match_time)


def populate_from_JSON(json, replay_in, session):
    def _fill_summaries_by_team(json, replay_in, team):
        assert(team in Team)
        smoke_summaries = list()
        players = list(replay_in.get_players(team))

        smoke_startend = get_smoke_summary(json, team)
        # Note times from this are not absolute time
        if smoke_startend is None:
            return smoke_summaries

        id = 0
        for start, end in smoke_startend:
            new_smoke = Smoke(replay_in)
            session.add(new_smoke)
            new_smoke.team = team
            new_smoke.startTime = start
            new_smoke.endTime = end
            new_smoke.id = id
            id += 1
            player_list = list()
            for p in players:
                if p.is_smoked_at(start, False) or p.is_smoked_at(start+1, False):
                    new_player = SmokedPlayers(new_smoke)
                    new_player.steam_id = p.steamID
                    new_player.player = p
                    player_list.append(new_player)

            new_smoke.players_smoked = player_list
            if len(player_list) == 0:
                print('''Smoke id: {} for team {} in {} has no smoked players
                         at start {} (or start +1)'''.format(id, team, start,
                         replay_in.replayID))
                new_smoke.averageXCoordinateStart = None
                new_smoke.averageYCoordinateStart = None
                new_smoke.averageXCoordinateEnd = None
                new_smoke.averageYCoordinateEnd = None

            else:
                cords_start = (
                    (p.get_position_at(start, relative_to_match_time=False).xCoordinate,
                    p.get_position_at(start, relative_to_match_time=False).yCoordinate)
                    for p in player_list
                    )
                cords_end = (
                    (p.get_position_at(end, relative_to_match_time=False).xCoordinate,
                    p.get_position_at(end, relative_to_match_time=False).yCoordinate)
                    for p in player_list
                    )

                x, y = average_coorinates(cords_start)
                new_smoke.averageXCoordinateStart = x
                new_smoke.averageYCoordinateStart = y

                x, y = average_coorinates(cords_end)
                new_smoke.averageXCoordinateEnd = x
                new_smoke.averageYCoordinateEnd = y

            session.merge(new_smoke)
            smoke_summaries.append(new_smoke)

        return smoke_summaries

    return _fill_summaries_by_team(json, replay_in, Team.DIRE) +\
        _fill_summaries_by_team(json, replay_in, Team.RADIANT)


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)