from sqlalchemy import (
    BigInteger, Column, ForeignKey, Integer, String, 
    Boolean, create_engine)
from sqlalchemy.types import Enum
from StaticAnalysis import LOG
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
    replay = relationship("Replay", back_populates="twin_gate")
    steamID = Column(BigInteger, primary_key=True)
    channel_start = Column(Integer, primary_key=True)
    channel_end = Column(Integer, primary_key=True)
    hero = Column(String)
    completes = Column(Boolean)
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


def populate_from_JSON(json, replay_in) -> List[TwinGate]:
    summary = get_twin_gates(json)
    gates = []

    for s in summary:
        gate = TwinGate(replay_in)
        gate.hero = s['hero']
        gate.channel_start = s['start'] - replay_in.creepSpawn
        gate.channel_end = s['end'] - replay_in.creepSpawn
        gate.completes = s['completed']
        gate.side_pos = get_gate_pos(s['startY'])
        # Get the steam ID and channel position for tormie pos
        for rp in replay_in.players:
            if rp.hero == s['hero']:
                gate.steamID = rp.steamID
                break
        if gate.steamID is None:
            LOG.warning(f"Could not asign steamID for {gate.hero} in {gate.replayID} at start {s['start']}")

        gates.append(gate)

    return gates


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)