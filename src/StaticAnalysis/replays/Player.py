from sqlalchemy import (BigInteger, Boolean, Column, Float, ForeignKey, String,
                        create_engine)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select
from sqlalchemy.types import Enum, Integer
from StaticAnalysis.lib.Common import relative_coordinate
from StaticAnalysis.replays import Base
# from .Replay import Replay, Team
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.JSONProcess import (get_accumulating_lists,
                                                get_pick_ban,
                                                get_player_created,
                                                get_player_status,
                                                get_player_team)


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
    status = relationship("PlayerStatus", #back_populates="player",
                          lazy="dynamic",
                          cascade="all, delete-orphan",
                          primaryjoin=
                          '''and_(PlayerStatus.steamID == Player.steamID,
                             PlayerStatus.replayID == Player.replayID)''',
                          )
    kills = relationship("Kills", lazy="select",
                         cascade="all, delete-orphan", primaryjoin=
                         '''and_(Kills.steam_ID == Player.steamID,
                            Kills.replay_ID == Player.replayID)''',
                         )
    assists = relationship("Assists", lazy="select",
                           cascade="all, delete-orphan", primaryjoin=
                           '''and_(Assists.steam_ID == Player.steamID,
                           Assists.replay_ID == Player.replayID)'''
                           )
    denies = relationship("Denies", lazy="select",
                          cascade="all, delete-orphan", primaryjoin=
                          '''and_(Denies.steam_ID == Player.steamID,
                          Denies.replay_ID == Player.replayID)'''
                          )
    deaths = relationship("Deaths", lazy="select",
                          cascade="all, delete-orphan", primaryjoin=
                          '''and_(Deaths.steam_ID == Player.steamID,
                          Deaths.replay_ID == Player.replayID)'''
                          )
    last_hits = relationship("LastHits", lazy="select",
                             cascade="all, delete-orphan", primaryjoin=
                             '''and_(LastHits.steam_ID == Player.steamID,
                             LastHits.replay_ID == Player.replayID)'''
                             )

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in

    def get_position_at(self, time, relative_to_match_time=False):
        ''' Get player position (x, y) at a global game time. '''
        # Array index starts from created_at
        if relative_to_match_time:
            time = time + self.replay.creepSpawn

        pos = self.status.filter(PlayerStatus.time == time).one_or_none()
        if pos is None:
            print("No entry for player at time {} trying + 1".format(time))
            pos = self.status.filter(PlayerStatus.time == time + 1).one_or_none()
        if pos is None:
            print("No entry for player at time {} trying - 1".format(time + 1))
            pos = self.status.filter(PlayerStatus.time == time - 1).one_or_none()
        if pos is None:
            print("No entry for player at time {} using created time.".format(time - 1))
            pos = self.status.filter(PlayerStatus.time == self.created_at).one()
        return pos

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
        if time < self.created_at:
            return False
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

    @hybrid_property
    def game_time(self):
        from .Replay import Replay
        creepSpawn = select([Replay.creepSpawn]).\
            where(self.replayID == Replay.replayID).as_scalar()
        return self.time - creepSpawn
    # Relationships
    # player = relationship(Player, back_populates="status", lazy="select")

    def __init__(self, player_in):
        # self.player = player_in
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
    increment = Column(Integer)

    @hybrid_property
    def game_time(self):
        from .Replay import Replay
        creepSpawn = select([Replay.creepSpawn]).\
            where(self.replayID == Replay.replayID).as_scalar()
        return self.time - creepSpawn


class Kills(CumulativePlayerStatus, Base):
    __tablename__ = "kills"


class Assists(CumulativePlayerStatus, Base):
    __tablename__ = "assists"


class Denies(CumulativePlayerStatus, Base):
    __tablename__ = "denies"
    denies = Column(Integer)


class Deaths(CumulativePlayerStatus, Base):
    __tablename__ = "deaths"


class LastHits(CumulativePlayerStatus, Base):
    __tablename__ = "lasthits"


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

    def _accumulating_stats(player, json):
        list_in = get_accumulating_lists(player.hero, json)
        assists = list()
        deaths = list()
        denies = list()
        kills = list()
        last_hits = list()

        for v in list_in["assists"]:
            new_class = Assists()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.increment = list_in["assists"][v]
            # new_class.player = player

            assists.append(new_class)
        
        for v in list_in["deaths"]:
            new_class = Deaths()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.increment = list_in["deaths"][v]
            # new_class.player = player

            deaths.append(new_class)

        for v in list_in["denies"]:
            new_class = Denies()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.increment = list_in["denies"][v]
            # new_class.player = player

            denies.append(new_class)

        for v in list_in["kills"]:
            new_class = Kills()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.increment = list_in["kills"][v]
            # new_class.player = player

            kills.append(new_class)

        for v in list_in["last_hits"]:
            new_class = LastHits()
            new_class.replay_ID = player.replayID
            new_class.steam_ID = player.steamID
            new_class.time = int(v)
            new_class.increment = list_in["last_hits"][v]
            # new_class.player = player

            last_hits.append(new_class)

        return {'assists': assists, 'deaths': deaths, 'denies': denies,
                'kills': kills, 'last_hits': last_hits}

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
        new_player.last_hits = accumulators['last_hits']

        session.add(new_player)
        players_out.append(new_player)

    return players_out


def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)
