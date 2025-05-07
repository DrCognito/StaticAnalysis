import json
from datetime import datetime

from herotools.HeroTools import HeroIDType, convertName
from sqlalchemy import (BigInteger, Column, DateTime, Integer, create_engine,
                        or_, Index)
from sqlalchemy.orm import relationship, Session, reconstructor
from sqlalchemy.types import Enum

from StaticAnalysis.replays import (Base, JSONProcess, Player, Rune, Scan,
                                    Smoke, TeamSelections, Ward, Tormentor, Stacks)
from StaticAnalysis.replays.Common import Team
from collections import Counter


class Replay(Base):
    __tablename__ = "Replays"

    replayID = Column(BigInteger, primary_key=True)
    endTimeUTC = Column(DateTime)
    gameStart = Column(Integer)
    creepSpawn = Column(Integer)
    gameEnd = Column(Integer)
    winner = Column(Enum(Team))
    league_ID = Column(Integer)

    # Relationships
    players = relationship(Player.Player, back_populates="replay",
                           lazy="select",
                           cascade="all, delete, delete-orphan",
                           )
    smoke_summary = relationship(Smoke.Smoke, back_populates="replay",
                                 lazy="dynamic",
                                 cascade="all, delete-orphan",
                                 #single_parent=True, passive_deletes='all'
                                 )
    teams = relationship(TeamSelections.TeamSelections,
                         back_populates="replay",
                         lazy="select",
                         cascade="all, delete-orphan",
                         #order_by=TeamSelections.TeamSelections.team,
                         #single_parent=True, passive_deletes='all'
                         )
    wards = relationship(Ward.Ward, back_populates="replay", lazy="dynamic",
                         cascade="all, delete-orphan",
                         # single_parent=True, passive_deletes=True
                         )
    scans = relationship(Scan.Scan, back_populates="replay", lazy="dynamic",
                         cascade="all, delete-orphan",
                         #single_parent=True, passive_deletes=True
                         )
    runes = relationship(Rune.Rune, back_populates="replay", lazy="dynamic",
                         cascade="all, delete-orphan",
                         #single_parent=True, passive_deletes=True
                         )
    tormentor_spawns = relationship(Tormentor.TormentorSpawn, back_populates="replay",
                                 lazy="dynamic",
                                 cascade="all, delete-orphan",
                                 #single_parent=True, passive_deletes='all'
                                 )
    tormentor_kills = relationship(Tormentor.TormentorKill, back_populates="replay",
                                 lazy="dynamic",
                                 cascade="all, delete-orphan",
                                 #single_parent=True, passive_deletes='all'
                                 )
    player_stacks = relationship(Stacks.PlayerStack, back_populates="replay",
                                 lazy="dynamic",
                                 cascade="all, delete-orphan",
                                 #single_parent=True, passive_deletes='all'
                                 )

    def get_player_by_hero(self, hero, nameType=HeroIDType.NPC_NAME):
        if nameType != HeroIDType.NPC_NAME:
            convertName(hero, nameType, HeroIDType.NPC_NAME)
        try:
            return next(p for p in self.players if p.hero == hero)
        except StopIteration:
            print("Player with hero {} not found in replay {}.".format(hero, self.replayID))
            return None

    def get_players(self, team=None):
        if team is None:
            yield from self.get_players(Team.DIRE)
            yield from self.get_players(Team.RADIANT)
            return

        assert(team in Team)
        yield from (p for p in self.players if p.team == team)

    @staticmethod
    def get_side_filter(team: Team, side):
        id_filter = Replay.teams.any((TeamSelections.TeamSelections.teamID == team.team_id) &
                                     (TeamSelections.TeamSelections.team == side))
        stack_filter = Replay.teams.any((TeamSelections.TeamSelections.stackID == team.stack_id) &
                                        (TeamSelections.TeamSelections.team == side))
        if team.extra_stackid is not None:
            assert team.extra_stackid != team.stack_id
            extra = Replay.teams.any((TeamSelections.TeamSelections.stackID == team.extra_stackid) &
                                     (TeamSelections.TeamSelections.team == side))

            final_filter = or_(id_filter, stack_filter, extra)
        else:
            final_filter = or_(id_filter, stack_filter)

        return final_filter
    
    @reconstructor
    def on_load(self):
        '''
        Runs after the object is loaded from the DB. Use to setup some useful stuff.
        '''
        ts: TeamSelections.TeamSelections
        for ts in self.teams:
            if ts.team == Team.RADIANT:
                self.radiant_id = ts.teamID
                self.radiant_name = ts.teamName
                if self.winner == Team.RADIANT:
                    self.winner_id = ts.teamID
            elif ts.team == Team.DIRE:
                self.dire_id = ts.teamID
                self.dire_name = ts.teamName
                if self.winner == Team.DIRE:
                    self.winner_id = ts.teamID
        self.player_team_map = {
            p: self.dire_id if p.team == Team.DIRE else self.radiant_id for p in self.players
        }
        # Also add steam IDs
        self.player_team_map.update(
            {
                p.steamID: self.dire_id if p.team == Team.DIRE else self.radiant_id for p in self.players
            }
        )
        self.player_side_map = {
            p.steamID:p.team for p in self.players
        }

    def first_pick(self):
        if self.teams[0].firstPick:
            return self.teams[0].team
        else:
            return self.teams[1].team

    def is_first_pick(self, team: 'TeamInfo'):
        """Helper function to test if team has first pick."""
        first_pick_side = self.first_pick()
        team_side = self.get_side(team)

        return first_pick_side == team_side

    PLAYER_NOTFOUND = object()
    def get_team_id_player(self, player: Player.Player | int):
        return self.player_team_map.get(player, Replay.PLAYER_NOTFOUND)

    def get_side(self, team: 'TeamInfo') -> Team:
        """Get side that a team is on or None if not found."""
        if self.teams[0].teamID == team.team_id:
            return self.teams[0].team
        if self.teams[1].teamID == team.team_id:
            return self.teams[1].team
        # Check by stack ID
        if self.teams[0].stackID == team.stack_id:
            return self.teams[0].team
        if self.teams[0].stackID == team.extra_stackid:
            return self.teams[0].team
        if self.teams[1].stackID == team.stack_id:
            return self.teams[1].team
        if self.teams[1].stackID == team.extra_stackid:
            return self.teams[1].team

        return None

    def is_radiant(self, team: 'TeamInfo') -> bool:
        """Helper function to check if team is radiant."""

        if self.get_side(team) == Team.RADIANT:
            return True
        return False

    def is_dire(self, team: 'TeamInfo') -> bool:
        """Helper function to check if team is dire."""

        if self.get_side(team) == Team.DIRE:
            return True
        return False

    def matching_players(self, player_set: set[int], side: Team) -> int:
        """Get number of matching players from a set for a side."""
        replay_set = {p.steamID for p in self.get_players(side)}
        intersection = player_set & replay_set

        return len(intersection)

    def get_team_dict(self) -> dict[Team, TeamSelections.TeamSelections]:
        for t in self.teams:
            if t.team == Team.DIRE:
                dire_team: TeamSelections = t
            else:
                radiant_team: TeamSelections = t

        return {Team.DIRE: dire_team, Team.RADIANT: radiant_team}
    
    def get_nice_side_name(self, team: Team, team_session: Session = None) -> str:
        '''
        Attempt to get a nice name for a team on side Team or a team matching a TeamInfo id.
        '''
        from StaticAnalysis.lib.team_info import get_player_teams, TeamInfo
        # Try the team ID first
        id_dict = self.get_team_dict()
        try:
            return TeamInfo.get_team_name(id_dict[team].teamID)
        except ValueError:
            # No such team id raises ValueError
            pass
        players = self.get_players(team)
        player_teams = get_player_teams(players, team_session)
        names = Counter(t.name for t in player_teams if t is not None)
        # Accept the most common if it is the majority
        try:
            name, c = names.most_common(1)[0] # (name, count)
        except IndexError:
            c = 0
        if c >= 3:
            return name
        # See if there is a name in the replay
        if id_dict[team].teamName is not None and id_dict[team].teamName != ' ':
            return id_dict[team].teamName

        return "Unknown"

replay_time_index = Index("idx_replay_endtime", Replay.replayID, Replay.endTimeUTC)

def InitDB(path):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)

    Player.InitDB(path)
    Smoke.InitDB(path)
    TeamSelections.InitDB(path)
    Ward.InitDB(path)
    Scan.InitDB(path)
    Rune.InitDB(path)
    Tormentor.InitDB(path)

    return engine


#https://stackoverflow.com/questions/13440905/sqlalchemy-return-existing-object-instead-of-creating-a-new-on-when-calling-con
def get_or_create(session, **kw):
    if len(kw) and "replayID" in kw:
        x = session.query(Replay).filter(Replay.replayID == kw['replayID'])\
                                 .one_or_none()
        if x:
            return x
    return Replay()


def populate_from_JSON_file(path, session, skip_existing=True):

    with open(path, 'r', encoding='utf8', errors="replace") as file:
        jsonFile = json.load(file)
        replay_ID = JSONProcess.get_replay_id(jsonFile, path)
        # Sometimes the replay_ID in the file is wrong and 0
        replay_query = session.query(Replay)\
                              .filter(Replay.replayID == replay_ID)
        if replay_query.count() == 1:
            if skip_existing:
                return replay_query.one()
            else:
                #replay_query.delete()
                session.delete(replay_query.one())
                session.flush()

        working_replay = Replay()
        session.add(working_replay)
        working_replay.replayID = JSONProcess.get_replay_id(jsonFile, path)
        working_replay.endTimeUTC = datetime.fromtimestamp(
                                        JSONProcess.get_end_time_UTC(jsonFile))
        working_replay.gameStart, working_replay.creepSpawn, working_replay.gameEnd =\
            JSONProcess.get_match_times(jsonFile)
        working_replay.winner = JSONProcess.get_winner(jsonFile)
        working_replay.league_ID = JSONProcess.get_league_id(jsonFile)

        working_replay.players = Player.populate_from_JSON(jsonFile,
                                                           working_replay,
                                                           session)

        working_replay.wards = Ward.populate_from_JSON(jsonFile,
                                                       working_replay, session)

        working_replay.scans = Scan.populate_from_JSON(jsonFile,
                                                       working_replay, session)

        working_replay.runes = Rune.populate_from_JSON(jsonFile,
                                                       working_replay, session)

        working_replay.smoke_summary = Smoke.populate_from_JSON(jsonFile,
                                                                working_replay,
                                                                session)

        working_replay.teams = TeamSelections.populate_from_JSON(jsonFile,
                                                                 working_replay,
                                                                 session)
        
        working_replay.tormentor_spawns, working_replay.tormentor_kills = Tormentor.populate_from_JSON(
            jsonFile, working_replay, session
        )
        
        working_replay.player_stacks = Stacks.populate_from_JSON(jsonFile, working_replay, session)

    session.merge(working_replay)
    return working_replay


def determine_side_byteam(team_id, replay):
    for t in replay.teams:
        if t.teamID == team_id:
            return t.team

    print("Failed to identify team {} in {}".format(team_id, replay.replayID))
    return None
