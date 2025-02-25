from StaticAnalysis import session, team_session
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.smoke_vis import smoke_start_locale, smoke_end_locale_first, smoke_end_locale_individual, get_smoke_time_info, get_smoke_time_players, get_smoked_player_table, get_smoke_table_replays
from sqlalchemy import or_
from StaticAnalysis.analysis.route_vis import get_player_dataframes
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.lib.Common import add_map, get_player_name, EXTENT, seconds_to_nice
from herotools.util import convert_to_32_bit
from typing import List

team_id = 8255888
def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team
team = get_team(team_id)

replays: List[Replay] = team.get_replays(session)
replay: Replay = replays[0]
side = replay.get_side(team)

positions = get_player_dataframes(
        replay, side, session,
        min_time=-90, max_time=45,
    )

player_list = [p.name for p in team.players]
order = []
names = []
player: Player
for player in replay.players:
    if player.team != side:
        continue
    try:
        name = get_player_name(team_session, player.steamID, team)
        order.append(player_list.index(name))
    except ValueError:
        name = player.steamID
        print(f"Player {player.steamID} ({convert_to_32_bit(player.steamID)})not found in {replay.replayID}")
        order.append(-1*player.steamID)
    names.append(name)

smoke_table = get_smoke_time_info(positions)
smoke_players = get_smoke_time_players(positions, names)
dire_summary_smoke = get_smoked_player_table(
    replays, team, Team.DIRE, session, team_session,
    min_time=8*60, max_time=15*60)
radiant_summary_smoke = get_smoked_player_table(
    replays, team, Team.RADIANT, session, team_session,
    min_time=-90, max_time=0)

loc_table = get_smoke_table_replays(
    replays, team, Team.DIRE, session, team_session,
    min_time=8*60, max_time=15*60)