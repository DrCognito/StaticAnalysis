from sqlalchemy import (
    BigInteger, Column, ForeignKey, Integer, String, 
    Boolean, create_engine)
from sqlalchemy.types import Enum
# from StaticAnalysis import LOG
from loguru import logger as LOG
from StaticAnalysis.lib.Common import EXTENT
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays import Base
from StaticAnalysis.replays.JSONProcess import get_twin_gates
from typing import List
from sqlalchemy.orm import relationship


class TwinGate(Base):
    __tablename__ = "twin_gates"
    replayID = Column(
        BigInteger, ForeignKey("Replays.replayID"),
        primary_key=True
        )
    replay = relationship("Replay", back_populates="twin_gates")
    steamID = Column(BigInteger, primary_key=True)
    channel_start = Column(Integer, primary_key=True)
    channel_end = Column(Integer, primary_key=True)
    hero = Column(String)
    hero_team = Column(Enum(Team))
    side_pos = Column(Enum(Team))

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in


def get_gate_pos(yPos: float) -> Team:
    # Use the player y_pos to get the position.
    yMin = EXTENT[2]
    yMax = EXTENT[3]

    diffMin = yPos - yMin
    diffMax = yMax - yPos

    # Closest to yMax is dire
    return Team.DIRE if diffMax < diffMin else Team.RADIANT


def populate_from_JSON(json, replay_in, session) -> List[TwinGate]:
    summary = get_twin_gates(json)
    gates = []

    for s in summary:
        if not s['completed']:
            continue
        gate = TwinGate(replay_in)
        gate.hero = s['hero']
        gate.channel_start = s['start'] - replay_in.creepSpawn
        gate.channel_end = s['end'] - replay_in.creepSpawn
        gate.side_pos = get_gate_pos(s['startY'])
        # Get the steam ID and channel position for tormie pos
        player = replay_in.get_player_by_hero(s['hero'])
        if player is not None:
            gate.steamID = player.steamID
            gate.hero_team = player.team
        else:
            LOG.warning(f"Could not asign player for {gate.hero} in {gate.replayID} at start {s['start']}. Missing steamID and hero_team.")

        session.add(gate)
        gates.append(gate)
        

    return gates


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)