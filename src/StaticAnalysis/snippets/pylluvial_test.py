import pylluvial as pa
from StaticAnalysis import session, team_session
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.route_vis import plot_pregame_players
from StaticAnalysis.analysis.smoke_vis import smoke_start_locale, smoke_end_locale_first, smoke_end_locale_individual
import matplotlib.pyplot as plt
from StaticAnalysis.replays.Player import Player, PlayerStatus
from pandas import read_sql
from herotools.location import get_player_location
from StaticAnalysis.lib.Common import get_player_name
from typing import List
from pandas import DataFrame, Series, concat
from numpy import arange

data_example = pa.generate_test_data(
    [3, 4, 3, 2]
)

replay = session.query(Replay).filter(Replay.replayID == 7957516700).one()
nigma = team_session.query(TeamInfo).filter(TeamInfo.team_id == 7554697).one()
avulus = team_session.query(TeamInfo).filter(TeamInfo.team_id == 9498970).one()

side = Team.DIRE
dire_player_loc = []
for player in replay.players:
    if player.team != side:
        continue
    query = player.status.filter(PlayerStatus.game_time <= 0)

    sql_query = query.with_entities(
        PlayerStatus.steamID,
        PlayerStatus.xCoordinate,
        PlayerStatus.yCoordinate,
        PlayerStatus.is_smoked,
        PlayerStatus.game_time,
        PlayerStatus.is_alive).statement

    p_df = read_sql(sql_query, session.bind)
    p_df['location'] = p_df.apply(
        lambda x: get_player_location(x['xCoordinate'], x['yCoordinate']),
        axis=1
        )
    p_df['name'] = p_df['steamID'].apply(
        lambda x: get_player_name(team_session, x, nigma)
        )
    dire_player_loc.append(p_df)

def player_status(row: Series):
    if not row['is_alive']:
        return 'dead'
    
    if row['is_smoked']:
        return 'smoked'

    return 'alive'


def df_timeline(times: List[int], data:DataFrame):
    out = data.loc[data['game_time'].isin(times)].copy()
    out['status'] = out.apply(lambda x: player_status(x), axis=1)

    return out

times = [-87, -40, 0]
times = arange(-87, 0, 10)
processed = [df_timeline(times, x) for x in dire_player_loc]
time_line_df = concat(processed)

# pass show_labels = True to get labelled plots
fig, ax = pa.alluvial(
    x = 'game_time',
    stratum = 'location',
    alluvium = 'name',
    # hue = 'status',
    palette = 'husl',
    data = time_line_df,
    stratum_gap = 2,
    stratum_width = 2,
    show_labels = True
)

fig.set_figwidth(10)
fig.set_figheight(5)
fig.tight_layout()