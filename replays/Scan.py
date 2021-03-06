from sqlalchemy import create_engine, Column, BigInteger, ForeignKey
from replays import Base
from sqlalchemy.orm import relationship
from .Common import Team
from .Player import Player
from .PositionTimeBase import PositionTimeBase
from .JSONProcess import get_scans
from datetime import timedelta
from lib.Common import relative_coordinate
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class Scan(PositionTimeBase, Base):
    __tablename__ = "scans"
    steamID = Column(BigInteger, ForeignKey(Player.steamID))

    # Relationships
    player = relationship(Player, lazy="select", primaryjoin=
                          "and_(Scan.steamID == Player.steamID, Scan.replayID == Player.replayID)",
                          #cascade="all, delete",
                          )
    replay = relationship("Replay", back_populates="scans", lazy="select")

    def __init__(self, replay_in):
        self.replay = replay_in
        self.replayID = replay_in.replayID


def populate_from_JSON(json, replay_in, session):
    scans_out = list()
    id = 0
    scan_object = get_scans(json)
    scan_object = zip(scan_object['xLoc'], scan_object['yLoc'],
                      scan_object['byHero'], scan_object['team'],
                      scan_object['timeList'])
    for x, y, hero, team, time in scan_object:
        new_scan = Scan(replay_in)
        new_scan.id = id
        id += 1

        new_scan.player = replay_in.get_player_by_hero(hero)
        new_scan.steamID = new_scan.player.steamID
        new_scan.time = time
        new_scan.xCoordinate = relative_coordinate(x)
        new_scan.yCoordinate = relative_coordinate(y)

        if team == 1:
            new_scan.team = Team.DIRE
        elif team == 0:
            new_scan.team = Team.RADIANT
        else:
            raise ValueError("Invalid team in scan.")

        # session.merge(new_scan)
        scans_out.append(new_scan)

    return scans_out


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)