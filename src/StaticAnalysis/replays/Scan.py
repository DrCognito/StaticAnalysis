from sqlalchemy import BigInteger, Column, ForeignKey, create_engine
from sqlalchemy.orm import relationship

from StaticAnalysis.lib.Common import relative_coordinate
from StaticAnalysis.replays import Base
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.JSONProcess import get_scans
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.PositionTimeBase import PositionTimeBase


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
    if scan_object is None:
        return scans_out
    scan_object = zip(scan_object['xLoc'], scan_object['yLoc'],
                      scan_object['byHero'], scan_object['team'],
                      scan_object['timeList'])
    for x, y, hero, team, time in scan_object:
        new_scan = Scan(replay_in)
        session.add(new_scan)
        new_scan.id = id
        id += 1

        new_scan.player = replay_in.get_player_by_hero(hero)
        new_scan.steamID = new_scan.player.steamID
        new_scan.game_time = time - replay_in.creepSpawn
        new_scan.xCoordinate = x
        new_scan.yCoordinate = y

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
    engine = create_engine(path)
    Base.metadata.create_all(engine)