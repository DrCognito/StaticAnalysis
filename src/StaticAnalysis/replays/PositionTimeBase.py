from sqlalchemy import Column, Integer, Float
from sqlalchemy import ForeignKey
from sqlalchemy.sql import select
from sqlalchemy.types import Enum
from sqlalchemy.ext.declarative import DeclarativeMeta, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from StaticAnalysis.replays.Common import Team
from abc import ABC


# The meta classes from SQLAlchemy and ABC must be combined to avoid
# a metaclass conflict as you may not inherit more than one at once.
# See: https://stackoverflow.com/questions/3626615/dealing-with-metaclass-conflict-with-sql-alchemy-declarative-base
#      https://blog.ionelmc.ro/2015/02/09/understanding-python-metaclasses/
class MetaABCDeclarativeMeta(DeclarativeMeta, ABC): pass


# class PositionTimeBase(MetaABCDeclarativeMeta):
class PositionTimeBase():
    @declared_attr
    def replayID(cls):
        return Column(Integer, ForeignKey("Replays.replayID"),
                      primary_key=True)
    id = Column(Integer, primary_key=True)
    time = Column(Integer)
    team = Column(Enum(Team), primary_key=True)
    xCoordinate = Column(Float)
    yCoordinate = Column(Float)

    @hybrid_property
    def game_time(self):
        return self.time - self.replay.creepSpawn

    @game_time.expression
    def game_time(self):
        from .Replay import Replay
        creepSpawn = select([Replay.creepSpawn]).\
            where(self.replayID == Replay.replayID).as_scalar()
        return self.time - creepSpawn

    @hybrid_property
    def winner(self):
        return self.team == self.replay.winner

    @winner.expression
    def winner(self):
        from .Replay import Replay
        winner = select([Replay.winner]).\
            where(self.replayID == Replay.replayID).as_scalar()
        return self.team == winner
