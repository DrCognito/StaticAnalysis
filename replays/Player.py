from sqlalchemy import Column, BigInteger, Float, Boolean
from sqlalchemy import create_engine, ForeignKey, String
from sqlalchemy.types import Enum, Integer
from sqlalchemy.orm import relationship
from replays import Base
# from .Replay import Replay, Team
from .Common import Team
from .JSONProcess import get_pick_ban, get_player_status, get_player_created
from .JSONProcess import get_player_smoketime, get_player_team, get_accumulating_lists
from lib.Common import relative_coordinate
import os
import sys
from sqlalchemy.ext.declarative import declared_attr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class Player(Base):
    __tablename__ = "player"
    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    steamID = Column(BigInteger, primary_key=True)
    hero = Column(String)
    team = Column(Enum(Team))
    created_at = Column(Integer)

    # Relationships
    replay = relationship("Replay", back_populates="players", lazy="select")
    status = relationship("PlayerStatus", back_populates="player",
                          lazy="dynamic",
                          cascade="all, delete-orphan", primaryjoin=
                          '''and_(PlayerStatus.steamID == Player.steamID,
                             PlayerStatus.replayID == Player.replayID)'''
                          )
    kills = relationship("Kills", back_populates="player", lazy="select",
                         cascade="all, delete-orphan", primaryjoin=
                         '''and_(Kills.steam_ID == Player.steamID,
                            Kills.replay_ID == Player.replayID)'''
                         )
    assists = relationship("Assists", back_populates="player", lazy="select",
                           cascade="all, delete-orphan", primaryjoin=
                           '''and_(Assists.steam_ID == Player.steamID,
                           Assists.replay_ID == Player.replayID)'''
                           )
    denies = relationship("Denies", back_populates="player", lazy="select",
                          cascade="all, delete-orphan", primaryjoin=
                          '''and_(Denies.steam_ID == Player.steamID,
                          Denies.replay_ID == Player.replayID)'''
                          )
    deaths = relationship("Deaths", back_populates="player", lazy="select",
                          cascade="all, delete-orphan", primaryjoin=
                          '''and_(Deaths.steam_ID == Player.steamID,
                          Deaths.replay_ID == Player.replayID)'''
                          )
    # smokes = relationship("PlayerSmoke", lazy="dynamic",
    #                       cascade="all, delete-orphan", primaryjoin=
    #                       '''and_(PlayerSmoke.steamID == Player.steamID,
    #                          PlayerSmoke.replayID == Player.replayID)''')

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in

    def get_position_at(self, time, relative_to_match_time=False):
        ''' Get player position (x, y) at a global game time. '''
        # Array index starts from created_at
        if relative_to_match_time:
            time = time + self.replay.creepSpawn

        return self.status.filter(PlayerStatus.time == time).one_or_none()

    def get_position_range(self, t1, t2, relative_to_match_time=False):
        ''' Get player position (x, y) for a global
            game time between t1 and t2.
            Time is inclusive.
            relative_to_match_time should be True for times based around the
            actual game. False is for times including picking etc.'''
        assert(t1 <= t2)
        if relative_to_match_time:
            t1 = t1 + self.replay.creepSpawn
            t2 = t2 + self.replay.creepSpawn

        # Time is inclusive
        return self.status.filter(PlayerStatus.time >= t1,
                                  PlayerStatus.time <= t2)

    def is_smoked_at(self, time, relative_to_match_time=False):
        if relative_to_match_time:
            time = time + self.replay.creepSpawn

        return self.status.filter(PlayerStatus.time == time).one().is_smoked
        # if self.smokes.filter(PlayerSmoke.start_time <= time,
        #                       PlayerSmoke.end_time >= time).count():
        #     return True
        # return False


class PlayerStatus(Base):
    __tablename__ = "playerstatus"
    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    steamID = Column(BigInteger, ForeignKey(Player.steamID), primary_key=True)
    time = Column(Integer, primary_key=True)

    xCoordinate = Column(Float)
    yCoordinate = Column(Float)

    is_smoked = Column(Boolean)
    is_alive = Column(Boolean)

    # Relationships
    player = relationship(Player, back_populates="status", lazy="select")

    def __init__(self, player_in):
        self.player = player_in
        self.replayID = player_in.replayID


# class PlayerSmoke(Base):
#     __tablename__ = "playersmokes"
#     replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
#                       primary_key=True)
#     steamID = Column(BigInteger, ForeignKey(Player.steamID), primary_key=True)

#     start_time = Column(Integer, primary_key=True)
#     end_time = Column(Integer)

#     # Relationships
#     player = relationship(Player, back_populates="smokes", lazy="select")

#     def __init__(self, player_in):
#         self.player = player_in
#         self.replayID = player_in.replayID

#     def get_smoke_positions(self):
#         return self.player.get_position_range(self.start_time, self.end_time)


class CumulativePlayerStatus():
    @declared_attr
    def replay_ID(cls):
        return Column(Integer, ForeignKey("Replays.replayID"),
                      primary_key=True)

    @declared_attr
    def steam_ID(cls):
        return Column(BigInteger, ForeignKey(Player.steamID),
                      primary_key=True)

    time = Column(Integer, primary_key=True)


class Kills(CumulativePlayerStatus, Base):
    __tablename__ = "kills"
    kills = Column(Integer)

    # Relationships
    player = relationship(Player, back_populates="kills", lazy="select")


class Assists(CumulativePlayerStatus, Base):
    __tablename__ = "assists"
    assists = Column(Integer)

    # Relationships
    player = relationship(Player, back_populates="assists", lazy="select")


class Denies(CumulativePlayerStatus, Base):
    __tablename__ = "denies"
    assists = Column(Integer)

    # Relationships
    player = relationship(Player, back_populates="denies", lazy="select")


class Deaths(CumulativePlayerStatus, Base):
    __tablename__ = "deaths"
    assists = Column(Integer)

    # Relationships
    player = relationship(Player, back_populates="deaths", lazy="select")


def populate_from_JSON(json, replay_in, session):
    players_out = list()
    pick_ban = get_pick_ban(json)

    def _positions(player, json):
        status_out = list()
        for t, (x, y, smoked, alive) in enumerate(get_player_status(
                                                  player.hero, json)):
            new_status = PlayerStatus(player)
            new_status.time = t + player.created_at
            new_status.xCoordinate = relative_coordinate(x)
            new_status.yCoordinate = relative_coordinate(y)
            new_status.is_smoked = smoked
            new_status.is_alive = alive

            # session.add(new_position)
            status_out.append(new_status)

        return status_out

    # def _smokes(player, json):
    #     smokes_out = list()
    #     smoke_times = get_player_smoketime(player.hero, json)

    #     for start, end in smoke_times:
    #         new_smoke = PlayerSmoke(player)
    #         new_smoke.start_time = start
    #         new_smoke.end_time = end

    #         # session.add(new_smoke)
    #         session.flush()
    #         smokes_out.append(new_smoke)

    #     return smokes_out
    def _accumulating_stats(player, json):
        list_in = get_accumulating_lists(player.hero, json)
        assists = list()
        deaths = list()
        denies = list()
        kills = list()
        
        for v in list_in["assists"]:
            new_class = Assists()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.assists = list_in["assists"][v]

            assists.append(new_class)
        
        for v in list_in["deaths"]:
            new_class = Deaths()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.deaths = list_in["deaths"][v]

            deaths.append(new_class)

        for v in list_in["denies"]:
            new_class = Denies()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.denies = list_in["denies"][v]

            denies.append(new_class)

        for v in list_in["kills"]:
            new_class = Kills()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.kills = list_in["kills"][v]

            kills.append(new_class)

        return {'assists': assists, 'deaths': deaths, 'denies': denies,
                'kills': kills}

    for hero, steam_ID in zip(pick_ban['playerHero'], pick_ban['steamID']):
        new_player = Player(replay_in)
        new_player.hero = hero
        new_player.steamID = steam_ID
        new_player.created_at = get_player_created(hero, json)
        new_player.team = get_player_team(hero, json)

        new_player.status = _positions(new_player, json)
        # new_player.smokes = _smokes(new_player, json)
        accumulators = _accumulating_stats(new_player, json)
        new_player.assists = accumulators['assists']
        new_player.deaths = accumulators['deaths']
        new_player.denies = accumulators['denies']
        new_player.kills = accumulators['kills']

        session.add(new_player)
        players_out.append(new_player)

    return players_out


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)
