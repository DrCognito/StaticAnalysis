from StaticAnalysis import session, team_session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import PlayerStatus, Player
from StaticAnalysis.replays.Rune import Rune, RuneID
from herotools.important_times import MAIN_TIME, ImportantTimes
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from sqlalchemy import and_, or_
from pandas import read_sql
import numpy as np
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.analysis.visualisation import plot_player_positioning
from StaticAnalysis.analysis.route_vis import plot_player_paths
from StaticAnalysis.analysis.Player import player_position_replays, player_positioning_single
from StaticAnalysis.analysis.rune import wisdom_rune_times, wisdom_rune_table, build_wisdom_rune_summary, plot_wisdom_table
from pandas import concat
from math import isnan
from StaticAnalysis.analysis.Player import player_heroes, player_position, player_position_replays, player_position_replay_id
import matplotlib.pyplot as plt
from StaticAnalysis.lib.Common import (add_map, EXTENT)
from StaticAnalysis.analysis.rune import plot_player_routes
from StaticAnalysis.lib.Common import get_player_name, convert_to_32_bit, DIRE_ANCIENT_COORD, RADIANT_ANCIENT_COORD
from StaticAnalysis.lib.team_info import get_player
from math import sqrt


def get_team(name) -> TeamInfo:
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team

team = get_team(8291895)
r_query = team.get_replays(session).filter(Replay.endTimeUTC >= MAIN_TIME)
rune_times = wisdom_rune_times(r_query, max_time=13 * 60)
rune_table = wisdom_rune_table(r_query, max_time=13*60)
start = 6.5 * 60

table_replays = []
r: Replay
for r in r_query:
    rune_max = rune_times[rune_times['replayID'] == r.replayID]['game_time'].max()
    if isnan(rune_max):
        print(f"No wisdom rune results for {r.replayID}")
        continue
    rune_max = int(rune_max)
    table_replays.append(player_position_replay_id(
        session, r.replayID,
        start=start, end=rune_max
        ))

table = concat(table_replays)

fig = plt.figure()
fig.set_size_inches(8.27, 8.27)
r_id = table['replayID'].unique()[0]
t_min_rune = rune_times[rune_times["replayID"] == r_id]["game_time"].min() - 30
t_max_rune = rune_times[rune_times["replayID"] == r_id]["game_time"].max()
replay_pos = table[
    (table["replayID"] == r_id) &
    (table["game_time"] > t_min_rune) &
    (table["game_time"] <= t_max_rune)
    ]

r: Replay = session.query(Replay).filter(Replay.replayID == str(r_id)).one_or_none()
if r:
    side = r.get_side(team)

axis = fig.subplots()
add_map(axis, extent=EXTENT)
plot_player_routes(replay_pos, team, axis)
# fig.subplots_adjust(wspace=0.04, left=0.06, right=0.94, top=0.97, bottom=0.04)


def get_player_name_simpler(pid: int):
    player: TeamPlayer = get_player(pid)
    if player is not None:
        return player.name
    else:
        return convert_to_32_bit(pid)

def get_playerobj(rid: int, pid: int, session = session):
    return session.query(Player).filter(Player.replayID == rid, Player.steamID == pid).one_or_none()


from pandas import DataFrame
def map_player_location_time(time_col, pid_col):
    x_col = []
    y_col = []
    pid: Player
    for t, pid in zip(time_col, pid_col):
        status: PlayerStatus = pid.get_position_at(t, relative_to_match_time=True)
        x_col.append(status.xCoordinate)
        y_col.append(status.yCoordinate)
    
    return x_col, y_col


def map_player_location_time2(time_col, pid_col, rid_col, use_game_time=True, session=session):
    if use_game_time:
        tvar = PlayerStatus.game_time
    else:
        tvar = PlayerStatus.time
    x_col = []
    y_col = []
    for t, pid, rid in zip(time_col, pid_col, rid_col):
        status: PlayerStatus = session.query(PlayerStatus).filter(
            PlayerStatus.steamID == pid,
            PlayerStatus.replayID == rid,
            tvar == t
        ).one_or_none()
        x_col.append(status.xCoordinate)
        y_col.append(status.yCoordinate)

    return x_col, y_col


def get_closest_ancient(x, y):
    vec_dire = (DIRE_ANCIENT_COORD[0] - x, DIRE_ANCIENT_COORD[1] - y)
    length_dire = sqrt(vec_dire[0]*vec_dire[0] +  vec_dire[1]*vec_dire[1])

    vec_radiant = (RADIANT_ANCIENT_COORD[0] - x, RADIANT_ANCIENT_COORD[1] - y)
    length_radiant = sqrt(vec_radiant[0]*vec_radiant[0] +  vec_radiant[1]*vec_radiant[1])
    
    if length_dire <= length_radiant:
        return Team.DIRE
    else:
        return Team.RADIANT

def get_closest_ancient_str(x, y):
    if get_closest_ancient(x, y) == Team.DIRE:
        return "Dire"
    return "Radiant"

# rune_table['Name'] = rune_table['steamID'].map(get_player_name_simpler)
# # rune_table['Player'] = rune_table.apply(lambda x: get_playerobj(x['replayID'], x['steamID']), axis=1)
# # rune_table['xCoordinate'], rune_table['yCoordinate'] = map_player_location_time(rune_table['game_time'], rune_table['Player'])
# rune_table['xCoordinate'], rune_table['yCoordinate'] = map_player_location_time2(rune_table['game_time'], rune_table['steamID'], rune_table['replayID'])
# rune_table['rune_loc'] = rune_table.apply(lambda x: get_closest_ancient(x['xCoordinate'], x['yCoordinate']), axis=1)
# rune_table['Stolen'] = rune_table['team'] != rune_table['rune_loc']

from StaticAnalysis.analysis.rune import build_wisdom_rune_summary

rune_table = build_wisdom_rune_summary(rune_table)
df = rune_table.loc[rune_table.loc[:,'replayID'] == r_id].drop('replayID', axis=1)
plot_wisdom_table(df, axis)
fig.tight_layout()
fig.savefig("rune_pos_test.png")
fig.clf()