from sqlalchemy import (BigInteger, Column, Float, ForeignKey, Integer, String, 
                        create_engine)
from StaticAnalysis.replays import Base
from StaticAnalysis.replays.JSONProcess import get_player_stacks
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum
from StaticAnalysis.replays.Common import Team


class PlayerStack(Base):
    __tablename__ = "player_camp_stacks"
    replayID = Column(
        BigInteger, ForeignKey("Replays.replayID"),
        primary_key=True
        )
    replay = relationship("Replay", back_populates="player_stacks")
    steamID = Column(BigInteger, primary_key=True)
    time = Column(Integer, primary_key=True)
    stacks = Column(Integer) # This is the cummulative amount
    game_time = Column(Integer)
    team = Column(Enum(Team))

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in


def populate_from_JSON(json, replay_in, session) -> list[PlayerStack]:
    output = []
    for hero, t, stacks in get_player_stacks(json):
        new_stack = PlayerStack(replay_in)
        new_stack.time = t
        new_stack.game_time = t - replay_in.creepSpawn
        new_stack.stacks = stacks
        
        for rp in replay_in.players:
            if rp.hero == hero:
                new_stack.steamID = rp.steamID
                new_stack.team = rp.team
                break
        
        session.add(new_stack)
        output.append(new_stack)
    
    return output

def __init__(self, replay_in):
    self.replayID = replay_in.replayID
    self.replay = replay_in