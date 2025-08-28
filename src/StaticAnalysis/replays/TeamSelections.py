from herotools.HeroTools import heroByID
from sqlalchemy import (BigInteger, Boolean, Column, ForeignKey, Integer,
                        String, create_engine)
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.sql import select
from sqlalchemy.types import Enum

from StaticAnalysis.replays import Base
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.JSONProcess import get_pick_ban, get_player_team, get_player_team_pb
from loguru import logger as LOG


class TeamSelections(Base):
    __tablename__ = "teamselections"

    replay_ID = Column(BigInteger, ForeignKey("Replays.replayID"),
                       primary_key=True)
    team = Column(Enum(Team), primary_key=True)
    teamID = Column(Integer)
    teamName = Column(String)
    stackID = Column(String)
    firstPick = Column(Boolean)

    # Relationships
    replay = relationship("Replay", back_populates="teams", lazy="select")
    draft = relationship("PickBans", lazy="select", primaryjoin=
                         '''and_(TeamSelections.replay_ID == PickBans.replayID,
                            TeamSelections.team == PickBans.team)''',
                         cascade="all, delete-orphan")

    def __init__(self, replay_in):
        self.replay = replay_in
        self.replay_ID = replay_in.replayID


class PickBans(Base):
    __tablename__ = "playerpicks"
    replayID = Column(BigInteger, ForeignKey("Replays.replayID"),
                      primary_key=True)
    order = Column(Integer, primary_key=True)
    team = Column(Enum(Team), ForeignKey(TeamSelections.team),
                  primary_key=True)
    hero = Column(String)
    is_pick = Column(Boolean)

    teamID = column_property(
        select(TeamSelections.teamID).
        where(replayID == TeamSelections.replay_ID).
        where(team == TeamSelections.team).scalar_subquery()
        .label("teamID")
    )

    from .Player import Player
    playerID = column_property(
        select(Player.steamID).
        where(replayID == Player.replayID).
        where(hero == Player.hero).scalar_subquery()
        .label("playerID")
    )


def populate_from_JSON(json, replay_in, session):
    from StaticAnalysis.analysis.table_picks_panda import CURRENT_PATCH
    def _process_team(json, replay_in, team):
        assert(team in Team)
        new_team = TeamSelections(replay_in)
        session.add(new_team)
        new_team.team = team

        pick_ban = get_pick_ban(json)
        team_res = zip(pick_ban['cName'], pick_ban['team'], pick_ban['isPick'], pick_ban['ID'])
        # team_res = [x for x in team_res if x[1] == team.value]

        pick_ban_list = list()
        order = 0
        for hero, t, is_pick, id in team_res:
            order += 1
            if t != team.value:
                continue
            new_pb = PickBans()
            session.add(new_pb)
            new_pb.replayID = replay_in.replayID
            new_pb.order = order
            if hero == "unknown_hero":
                try:
                    hero = heroByID[int(id)]
                except KeyError:
                    LOG.warning(f"Could not convert hero in pick ban list! {id}")
            new_pb.hero = hero
            new_pb.is_pick = is_pick

            pick_ban_list.append(new_pb)
        if len(pick_ban_list) == 0:
            # Often happens with redrafts so we only have picks
            # No first pick info without pickbans so just pick one
            orders = CURRENT_PATCH.first_pick if team == Team.DIRE else CURRENT_PATCH.second_pick
            pick_order = 0
            LOG.warning(f"[TeamSelections] Could not populate PickBans from PicksAndBans in replay, using Player.")

            for hero in pick_ban['playerHero']:
                p_team = get_player_team(hero, json)
                try:
                    p_team = get_player_team(hero, json)
                except ValueError:
                    LOG.warning(f"Could not determine team from hero object for {hero} in {replay_in.replayID}")
                    p_team = get_player_team_pb(hero, json)
                if p_team != team:
                    continue
                new_pb = PickBans()
                new_pb.replayID = replay_in.replayID
                new_pb.is_pick = True
                new_pb.order = orders[pick_order]
                pick_order += 1
                new_pb.hero = hero
                
                pick_ban_list.append(new_pb)

        new_team.draft = pick_ban_list

        if team == Team.DIRE:
            new_team.teamID = pick_ban["direTeamID"]
            new_team.teamName = pick_ban["direTeamName"]
        elif team == Team.RADIANT:
            new_team.teamID = pick_ban["radiantTeamID"]
            new_team.teamName = pick_ban["radiantTeamName"]

        new_team.stackID = get_stack_id(replay_in, team)
        # Sometimes when a game is re-made there is no pick information.
        # Mostly this just works, but this explicit index can raise an
        # exception.
        try:
            new_team.firstPick = Team(pick_ban['team'][0]) == team
        except IndexError:
            new_team.firstPick = None

        session.merge(new_team)
        return new_team

    return [_process_team(json, replay_in, Team.DIRE),
            _process_team(json, replay_in, Team.RADIANT)]


def get_stack_id(replay, team):
    ''' Get all the steam ids for a team then sort them low to high
        and output as string. '''
    assert(team in Team)
    player_ids = list()

    for p in replay.get_players(team):
        player_ids.append(p.steamID)

    player_ids.sort()

    return ''.join(str(i) for i in player_ids)


def InitDB(path):
    engine = create_engine(path)
    Base.metadata.create_all(engine)
