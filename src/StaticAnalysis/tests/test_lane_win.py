from StaticAnalysis.tests.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Player import Player, NetWorth, PlayerStatus
from StaticAnalysis.analysis.Player import player_positioning_replay, closest_tower
from StaticAnalysis.lib.Common import dire_towers, radiant_towers
from pandas import DataFrame, read_sql
import pandas as pd

test_replay = 7290518726
timelimit = 60*7

r_query = session.query(NetWorth).filter(NetWorth.replayID == test_replay)
# t_query = r_query.filter(NetWorth.game_time == 600).with_entities(NetWorth.hero, NetWorth.networth)
b_query = session.query(NetWorth.replayID, NetWorth.hero, NetWorth.team, NetWorth.networth).filter(NetWorth.replayID == test_replay, NetWorth.game_time == 600)
# test = b_query.with_entities(NetWorth.hero, NetWorth.networth)
df = read_sql(b_query.statement, session.bind).sort_values(by=['networth'], ascending=False)

# Grouping example with agg
grouper = df.groupby(by=['team'])
grouper.agg({'hero': list, 'networth': max})

player_pos = player_positioning_replay(session, test_replay, start=0, end=timelimit, alive_only=True)
player_pos = player_pos.with_entities(PlayerStatus.hero,
                                      PlayerStatus.xCoordinate,
                                      PlayerStatus.yCoordinate,
                                      PlayerStatus.team)

pos = read_sql(player_pos.statement, session.bind)


def asign_lane(row):
    x = row['xCoordinate']
    y = row['yCoordinate']
    if row['team'] == Team.DIRE:
        tower_dict = dire_towers
    if row['team'] == Team.RADIANT:
        tower_dict = radiant_towers

    return closest_tower((x, y), tower_dict)


# Asign a lane each second, get max value count after
pos['lane'] = pos.apply(asign_lane, axis=1)
pos.groupby(by=['team', 'hero',])['lane'].apply(lambda x: x.value_counts().index[0]) 
