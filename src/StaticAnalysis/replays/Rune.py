import enum

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, create_engine
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select
from sqlalchemy.types import Enum

from StaticAnalysis.replays import Base
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.JSONProcess import get_rune_list
from StaticAnalysis.replays.Player import Player


class RuneID(enum.Enum):
    DoubleDamage = 0
    Haste = 1
    Illusion = 2
    Invisibility = 3
    Regeneration = 4
    Bounty = 5
    Arcane = 6
    WaterRune = 7
    Wisdom = 8
    Shield = 9


class Rune(Base):
    __tablename__ = "runes"
    runeType = Column(Enum(RuneID))
    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    id = Column(Integer, primary_key=True)
    time = Column(Integer)
    team = Column(Enum(Team), primary_key=True)
    steamID = Column(BigInteger, ForeignKey(Player.steamID))

    # Relationships
    player = relationship(Player, lazy="select", primaryjoin=
                          "and_(Rune.steamID == Player.steamID, Rune.replayID == Player.replayID)")
    replay = relationship("Replay", back_populates="runes")

    def __init__(self, replay_in):
        self.replay = replay_in
        self.replayID = replay_in.replayID

    @hybrid_property
    def game_time(self):
        return self.time - self.replay.creepSpawn

    @game_time.expression
    def game_time(self):
        from .Replay import Replay
        creepSpawn = select([Replay.creepSpawn]).\
            where(self.replayID == Replay.replayID).as_scalar()
        return self.time - creepSpawn


def populate_from_JSON(json, replay_in, session):
    if (rune_list := get_rune_list(json)) is None:
        return []
    runes_out = list()
    id = 0
    for r in rune_list:
        new_rune = Rune(replay_in)
        new_rune.id = id
        id += 1

        new_rune.player = replay_in.get_player_by_hero(r['unitName'])
        new_rune.steamID = new_rune.player.steamID
        new_rune.time = r['time']
        new_rune.runeType = RuneID(r['runeValue'])

        if r['team'] == 'DIRE':
            new_rune.team = Team.DIRE
        elif r['team'] == 'RADIANT':
            new_rune.team = Team.RADIANT
        else:
            raise ValueError("Invalid team in rune.")

        # session.merge(new_rune)
        runes_out.append(new_rune)

    return runes_out


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)
