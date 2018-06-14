from sqlalchemy import Column, Integer, BigInteger, DateTime, Float
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.types import Enum, Integer
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import relationship
from replays import Base
from datetime import datetime
from . import Player
from . import Ward
from . import Scan
from . import Rune
from . import Smoke
from . import TeamSelections
import json
from . import JSONProcess
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.HeroTools import convertName, HeroIDType
from .Common import Team


class Replay(Base):
    __tablename__ = "Replays"

    replayID = Column(BigInteger, primary_key=True)
    endTimeUTC = Column(DateTime)
    gameStart = Column(Integer)
    creepSpawn = Column(Integer)
    gameEnd = Column(Integer)
    winner = Column(Enum(Team))
    league_ID = Column(Integer)

    # Relationships
    players = relationship(Player.Player, back_populates="replay",
                           lazy="select",
                           cascade="all, delete-orphan")
    smoke_summary = relationship(Smoke.Smoke, back_populates="replay",
                                 lazy="select",
                                 cascade="all, delete-orphan")
    teams = relationship(TeamSelections.TeamSelections,
                         back_populates="replay",
                         lazy="select",
                         cascade="all, delete-orphan")
    wards = relationship(Ward.Ward, back_populates="replay", lazy="dynamic",
                         cascade="all, delete-orphan")
    scans = relationship(Scan.Scan, back_populates="replay", lazy="dynamic",
                         cascade="all, delete-orphan")
    runes = relationship(Rune.Rune, back_populates="replay", lazy="dynamic",
                         cascade="all, delete-orphan")

    def get_player_by_hero(self, hero, nameType=HeroIDType.NPC_NAME):
        if nameType != HeroIDType.NPC_NAME:
            convertName(hero, nameType, HeroIDType.NPC_NAME)
        try:
            return next(p for p in self.players if p.hero == hero)
        except StopIteration:
            print("Player with hero {} not found in replay.".format(hero))
            return None

    def get_players(self, team=None):
        if team is None:
            yield from self.get_players(Team.DIRE)
            yield from self.get_players(Team.RADIANT)
            return

        assert(team in Team)
        yield from (p for p in self.players if p.team == team)


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)

    Player.InitDB(path)
    Smoke.InitDB(path)
    TeamSelections.InitDB(path)
    Ward.InitDB(path)
    Scan.InitDB(path)
    Rune.InitDB(path)

    return engine


def populate_from_JSON_file(path, session):
    newReplay = Replay()

    with open(path, 'r', encoding='utf8', errors="replace") as file:
        jsonFile = json.load(file)

        newReplay.replayID = JSONProcess.get_replay_id(jsonFile)
        newReplay.endTimeUTC = datetime.fromtimestamp(
                                        JSONProcess.get_end_time_UTC(jsonFile))
        newReplay.gameStart, newReplay.creepSpawn, newReplay.gameEnd =\
            JSONProcess.get_match_times(jsonFile)
        newReplay.winner = JSONProcess.get_winner(jsonFile)
        newReplay.league_ID = JSONProcess.get_league_id(jsonFile)

        newReplay.players = Player.populate_from_JSON(jsonFile, newReplay,
                                                      session)

        newReplay.wards = Ward.populate_from_JSON(jsonFile, newReplay, session)

        newReplay.scans = Scan.populate_from_JSON(jsonFile, newReplay, session)

        newReplay.runes = Rune.populate_from_JSON(jsonFile, newReplay, session)

        newReplay.smoke_summary = Smoke.populate_from_JSON(jsonFile, newReplay,
                                                           session)

        newReplay.teams = TeamSelections.populate_from_JSON(jsonFile,
                                                            newReplay, session)

    session.merge(newReplay)
    return newReplay


def determine_side_byteam(team_id, replay):
    for t in replay.teams:
        if t.teamID == team_id:
            return t.team

    print("Failed to identify team {} in {}".format(team_id, replay.replayID))
    return None
