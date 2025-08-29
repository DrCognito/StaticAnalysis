from sqlalchemy import (BigInteger, Boolean, Column, Float, ForeignKey, String,
                        create_engine, Index)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, column_property
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
                                                get_player_team,
                                                get_net_worth,
                                                get_player_team_pb)
from sqlalchemy.orm import aliased
from sqlalchemy import inspect
from loguru import logger as LOG
# from StaticAnalysis.replays.Replay import Replay


class Player(Base):
    __tablename__ = "player"
    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    steamID = Column(BigInteger, primary_key=True)
    hero = Column(String)
    team = Column(Enum(Team))
    created_at = Column(Integer)
    
    @hybrid_property
    def win(self):
        from .Replay import Replay
        winner = select(Replay.winner).\
            where(self.replayID == Replay.replayID).scalar_subquery()
        return self.team == winner
    
    @hybrid_property
    def endGameTime(self):
        from .Replay import Replay
        return (
            select(Replay.endTimeUTC)
            .where(self.replayID == Replay.replayID)
            .scalar_subquery()
            .label("endGameTime")
        )

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
    net_worth = relationship("NetWorth", lazy="dynamic",
                             cascade="all, delete-orphan", primaryjoin=
                             '''and_(NetWorth.steamID == Player.steamID,
                             NetWorth.replayID == Player.replayID)''',
                             back_populates="player"
                             )
    # net_worth = relationship("NetWorth", back_populates="player", foreign_keys=["NetWorth.replayID", "Networth.steamID"])

    def __init__(self, replay_in):
        self.replayID = replay_in.replayID
        self.replay = replay_in

    def get_position_at(self, time, relative_to_match_time=True):
        ''' Get player position (x, y) at a global game time. '''
        # Array index starts from created_at
        if not relative_to_match_time:
            time = time - self.replay.creepSpawn

        pos = self.status.filter(PlayerStatus.game_time == time).one_or_none()
        if pos is None:
            print("No entry for player at time {} trying + 1".format(time))
            pos = self.status.filter(PlayerStatus.game_time == time + 1).one_or_none()
        if pos is None:
            print("No entry for player at time {} trying - 1".format(time + 1))
            pos = self.status.filter(PlayerStatus.game_time == time - 1).one_or_none()
        if pos is None:
            print("No entry for player at time {} using created time.".format(time - 1))
            pos = self.status.filter(PlayerStatus.game_time == self.created_at).one()
        return pos

    def get_position_range(self, t1, t2, relative_to_match_time=True):
        ''' Get player position (x, y) for a global
            game time between t1 and t2.
            Time is inclusive.
            relative_to_match_time should be True for times based around the
            actual game. False is for times including picking etc.'''
        assert(t1 <= t2)
        if not relative_to_match_time:
            t1 = t1 - self.replay.creepSpawn
            t2 = t2 - self.replay.creepSpawn

        # Time is inclusive
        return self.status.filter(PlayerStatus.game_time >= t1,
                                  PlayerStatus.game_time <= t2)
    
    
    def get_networth_at(self, game_time: int) -> int | None:
        nw = self.net_worth.filter(NetWorth.game_time == game_time).one_or_none()
        if nw is not None:
            nw = nw.networth
        return nw
    

    def is_smoked_at(self, time, relative_to_match_time=True):
        if not relative_to_match_time:
            time = time - self.replay.creepSpawn
        if time + self.replay.creepSpawn < self.created_at:
            return False
        return self.status.filter(PlayerStatus.game_time == time).one().is_smoked



class PlayerStatus(Base):
    __tablename__ = "playerstatus"
    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    steamID = Column(BigInteger, ForeignKey(Player.steamID), primary_key=True)
    game_time = Column(Integer, primary_key=True)

    xCoordinate = Column(Float)
    yCoordinate = Column(Float)

    is_smoked = Column(Boolean)
    is_alive = Column(Boolean)

    team_id = Column(Integer)

    @hybrid_property
    def time(self):
        from .Replay import Replay
        creepSpawn = select(Replay.creepSpawn).\
            where(self.replayID == Replay.replayID).scalar_subquery()
        return self.game_time + creepSpawn

    @hybrid_property
    def hero(self) -> str:
        return (
            select(Player.hero)
            .where(Player.replayID == self.replayID)
            .where(Player.steamID == self.steamID)
            .label("hero")
        )

    @hybrid_property
    def team(self) -> Team:
        return (
            select(Player.team)
            .where(Player.replayID == self.replayID)
            .where(Player.steamID == self.steamID)
            .scalar_subquery()
            .label("team")
        )

    def __init__(self, player_in):
        # self.player = player_in
        self.replayID = player_in.replayID

player_status_index = Index("idx_playerstatus_primaries", PlayerStatus.replayID, PlayerStatus.steamID, PlayerStatus.game_time)

class NetWorth(Base):
    __tablename__ = "networth"
    replayID = Column(BigInteger, ForeignKey(Player.replayID),
                      primary_key=True)
    steamID = Column(BigInteger, ForeignKey(Player.steamID), primary_key=True)
    game_time = Column(Integer, primary_key=True)

    networth = Column(Integer)

    @hybrid_property
    def time(self):
        from .Replay import Replay
        creepSpawn = select(Replay.creepSpawn).\
            where(self.replayID == Replay.replayID).scalar_subquery()
        return self.game_time + creepSpawn

    @hybrid_property
    def hero(self) -> str:
        return self.player.hero

    @hero.expression
    def hero(cls) -> str:
        return (
            select(Player.hero)
            .where(Player.replayID == cls.replayID)
            .where(Player.steamID == cls.steamID)
            .label("hero")
        )

    @hybrid_property
    def team(self) -> Team:
        return self.player.team

    @team.expression
    def team(cls) -> Team:
        return (
            select(Player.team)
            .where(Player.replayID == cls.replayID)
            .where(Player.steamID == cls.steamID)
            .label("team")
        )

    # player = relationship(Player, back_populates="status", lazy="select")
    player = relationship("Player", back_populates="net_worth", primaryjoin=
                             '''and_(NetWorth.steamID == Player.steamID,
                                NetWorth.replayID == Player.replayID)''')

    def __init__(self, player_in):
        # self.player = player_in
        self.replayID = player_in.replayID


class CumulativePlayerStatus():
    @declared_attr
    def replay_ID(cls):
        return Column(Integer, ForeignKey("Replays.replayID"),
                      primary_key=True)

    @declared_attr
    def steam_ID(cls):
        return Column(BigInteger, ForeignKey(Player.steamID),
                      primary_key=True)

    game_time = Column(Integer, primary_key=True)
    increment = Column(Integer)

    @hybrid_property
    def time(self):
        from .Replay import Replay
        creepSpawn = select(Replay.creepSpawn).\
            where(self.replayID == Replay.replayID).scalar_subquery()
        return self.game_time + creepSpawn


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

    def _positions(player, json, radiant_id, dire_id):
        status_out = list()
        for t, (x, y, smoked, alive) in enumerate(get_player_status(
                                                  player.hero, json)):
            new_status = PlayerStatus(player)
            session.add(new_status)
            new_status.game_time = t + player.created_at - replay_in.creepSpawn
            new_status.xCoordinate = x
            new_status.yCoordinate = y
            new_status.is_smoked = smoked
            new_status.is_alive = alive
            
            if player.team == Team.RADIANT:
                new_status.team_id = radiant_id
            elif player.team == Team.DIRE:
                new_status.team_id = dire_id
            else:
                raise ValueError(f"No team id for player {player.steamID}, {replay_in.replayID}")

            status_out.append(new_status)

        return status_out

    def _networth(player, json):
        net_worth = list()
        try:
            for t, gp in enumerate(get_net_worth(player.hero, json)):
                new_class = NetWorth(player)
                session.add(new_class)
                new_class.steamID = player.steamID
                new_class.game_time = t + player.created_at - replay_in.creepSpawn
                new_class.networth = gp

                net_worth.append(new_class)
        except ValueError:
            LOG.warning(f"Missing networth data for {hero} in {replay_in.replayID}")

        return net_worth

    def _accumulating_stats(player, json):
        list_in = get_accumulating_lists(player.hero, json)
        assists = list()
        deaths = list()
        denies = list()
        kills = list()
        last_hits = list()

        if list_in["assists"] is not None:
            for v in list_in["assists"]:
                new_class = Assists()
                session.add(new_class)
                new_class.replay_ID = player.replayID
                new_class.steam_ID = player.steamID
                new_class.game_time = int(v) - replay_in.creepSpawn
                new_class.increment = list_in["assists"][v]
                # new_class.player = player

                assists.append(new_class)
        
        if list_in["deaths"] is not None:
            for v in list_in["deaths"]:
                new_class = Deaths()
                session.add(new_class)
                new_class.replay_ID = player.replayID
                new_class.steam_ID = player.steamID
                new_class.game_time = int(v) - replay_in.creepSpawn
                new_class.increment = list_in["deaths"][v]
                # new_class.player = player

                deaths.append(new_class)

        if list_in["denies"] is not None:
            for v in list_in["denies"]:
                new_class = Denies()
                session.add(new_class)
                new_class.replay_ID = player.replayID
                new_class.steam_ID = player.steamID
                new_class.game_time = int(v) - replay_in.creepSpawn
                new_class.increment = list_in["denies"][v]
                # new_class.player = player

                denies.append(new_class)

        if list_in["kills"] is not None:
            for v in list_in["kills"]:
                new_class = Kills()
                session.add(new_class)
                new_class.replay_ID = player.replayID
                new_class.steam_ID = player.steamID
                new_class.game_time = int(v) - replay_in.creepSpawn
                new_class.increment = list_in["kills"][v]
                # new_class.player = player

                kills.append(new_class)

        if list_in["last_hits"] is not None:
            for v in list_in["last_hits"]:
                new_class = LastHits()
                session.add(new_class)
                new_class.replay_ID = player.replayID
                new_class.steam_ID = player.steamID
                new_class.game_time = int(v) - replay_in.creepSpawn
                new_class.increment = list_in["last_hits"][v]
                # new_class.player = player

                last_hits.append(new_class)

        return {'assists': assists, 'deaths': deaths, 'denies': denies,
                'kills': kills, 'last_hits': last_hits}

    for ts in replay_in.teams:
        if ts.team == Team.RADIANT:
            radiant_id = ts.teamID
        elif ts.team == Team.DIRE:
            dire_id = ts.teamID
    for hero, steam_ID in zip(pick_ban['playerHero'], pick_ban['steamID']):
        new_player = Player(replay_in)
        session.add(new_player)
        new_player.hero = hero
        new_player.steamID = steam_ID
        new_player.created_at = get_player_created(hero, json)
        try:
            new_player.team = get_player_team(hero, json)
        except ValueError:
            LOG.warning(f"Could not determine team from hero object for {hero} in {replay_in.replayID}")
            new_player.team = get_player_team_pb(hero, json)

        new_player.status = _positions(new_player, json, radiant_id, dire_id)
        # new_player.smokes = _smokes(new_player, json)
        accumulators = _accumulating_stats(new_player, json)
        new_player.assists = accumulators['assists']
        new_player.deaths = accumulators['deaths']
        new_player.denies = accumulators['denies']
        new_player.kills = accumulators['kills']
        new_player.last_hits = accumulators['last_hits']
        new_player.net_worth = _networth(new_player, json)

        session.add(new_player)
        players_out.append(new_player)

    return players_out


def InitDB(path):
    from StaticAnalysis.replays.TeamSelections import TeamSelections
    # My understanding of how this works is retrieving the team has to be from a second instance of PlayerStatus
    # This is p_status.
    # p_status also has to be "set" to the current PlayerStatus with the first two lines or it uses first result (Alliance)
    # p_status: PlayerStatus = aliased(PlayerStatus)
    # inspect(PlayerStatus).add_property(
    #     "team_id",
    #     column_property(
    #         select(TeamSelections.teamID)
    #         .where(p_status.replayID == PlayerStatus.replayID)
    #         .where(p_status.steamID == PlayerStatus.steamID)
    #         .where(TeamSelections.replay_ID == p_status.replayID)
    #         .where(TeamSelections.team == p_status.team)
    #         .scalar_subquery()
    #         .label("team_id")
    #     )
    # )
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)
    # player_status_index.create(bind=engine)