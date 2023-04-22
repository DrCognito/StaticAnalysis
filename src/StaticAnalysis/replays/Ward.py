from sqlalchemy import BigInteger, Column, ForeignKey, create_engine, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum

from StaticAnalysis.lib.Common import relative_coordinate
from StaticAnalysis.replays import Base
from StaticAnalysis.replays.Common import Team, WardType
from StaticAnalysis.replays.JSONProcess import get_wards
from StaticAnalysis.replays.Player import Player, PlayerStatus
from StaticAnalysis.replays.PositionTimeBase import PositionTimeBase


class Ward(PositionTimeBase, Base):
    __tablename__ = "wards"
    ward_type = Column(Enum(WardType))
    steamID = Column(BigInteger, ForeignKey(Player.steamID))

    # Relationships
    player = relationship(Player, lazy="select", primaryjoin=
                          "and_(Ward.steamID == Player.steamID, Ward.replayID == Player.replayID)")
    replay = relationship("Replay", back_populates="wards", lazy="select")

    @hybrid_property
    def from_smoke(self):
        return self.player.is_smoked_at(self.time)

    @from_smoke.expression
    def from_smoke(self):
        is_smoked = select([PlayerStatus.is_smoked])\
                        .where(PlayerStatus.replayID == self.replayID)\
                        .where(PlayerStatus.steamID == self.steamID)\
                        .where(PlayerStatus.time == self.time)\
                        .as_scalar()

        return is_smoked

    def __init__(self, replay_in):
        self.replay = replay_in
        self.replayID = replay_in.replayID


def populate_from_JSON(json, replay_in, session):
    wards_out = list()
    id = 0
    for w in get_wards(json):
        new_ward = Ward(replay_in)
        new_ward.id = id
        id += 1

        new_ward.ward_type = WardType(w['wardType'])
        try:
            new_ward.player = replay_in.get_player_by_hero(w['cName'])
        except KeyError as err:
            print(f"Bad ward hero key!: {w}")
        if new_ward.player is None:
            new_ward.steamID = None
        else:
            new_ward.steamID = new_ward.player.steamID
        new_ward.time = w['time']
        new_ward.xCoordinate = w['preciseX']
        new_ward.yCoordinate = w['preciseY']

        if w['team'] == 'DIRE':
            new_ward.team = Team.DIRE
        elif w['team'] == 'RADIANT':
            new_ward.team = Team.RADIANT
        else:
            raise ValueError("Invalid team in ward.")

        # session.merge(new_ward)
        wards_out.append(new_ward)

    return wards_out


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)