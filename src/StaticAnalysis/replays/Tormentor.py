from sqlalchemy import (BigInteger, Column, Float, ForeignKey, Integer, String, 
                        create_engine)
from StaticAnalysis.replays import Base
from StaticAnalysis.replays.JSONProcess import get_tormentor_summary
from typing import Tuple, List


class TormentorSpawn(Base):
    __tablename__ = "tormentor_spawns"
    replayID = Column(
        BigInteger, ForeignKey("Replays.replayID"),
        primary_key=True
        )
    time = Column(Integer, primary_key=True)
    game_time = Column(Integer)
    xCoordinate = Column(Float)
    yCoordinate = Column(Float)

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in

class TormentorKill(Base):
    __tablename__ = "tormentor_kills"
    replayID = Column(
        BigInteger, ForeignKey("Replays.replayID"),
        primary_key=True
        )
    time = Column(Integer, primary_key=True)
    game_time = Column(Integer)
    steamID = Column(BigInteger)
    hero = Column(String)

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in

def populate_from_JSON(json, replay_in, session) -> Tuple[List[TormentorSpawn], List[TormentorKill]]:
    summary = get_tormentor_summary(json)
    spawns = []
    spawn_iter = zip(
        summary['tormentorSpawnTime'],
        summary['tormentorXcoord'],
        summary['tormentorYcoord'],
    )
    for t, x, y in spawn_iter:
        spawn = TormentorSpawn(replay_in)

        spawn.time = t
        spawn.game_time = t - replay_in.creepSpawn
        spawn.xCoordinate = x
        spawn.yCoordinate = y

        session.add(spawn)
        spawns.append(spawn)

    kills = []
    for t, p in zip(summary['tormentorDeathTimes'], summary['tormentorKillers']):
        kill = TormentorKill(replay_in)
        
        kill.time = t
        kill.game_time = t - replay_in.creepSpawn
        
        kill.hero = p
        steamID = None
        for rp in replay_in.players:
            if rp.hero == p:
                steamID = rp.steamID
            break
        if steamID is None:
            print(f"Could not assign tormentor kill @ {t} from hero {p} a steamID")
        kill.steamID = steamID

        session.add(kill)
        kills.append(kill)

    return spawns, kills

def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)