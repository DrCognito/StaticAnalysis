from StaticAnalysis.snippets.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Player import Player, NetWorth, PlayerStatus
from StaticAnalysis.analysis.Player import player_positioning_replay, closest_tower
from StaticAnalysis.lib.Common import dire_towers, radiant_towers
from sqlalchemy import select, distinct
from pandas import DataFrame, read_sql
import pandas as pd
from StaticAnalysis.analysis.networth import (
    get_lane_results, plot_networth_bar, scheme_geo, scheme_log)
import matplotlib.pyplot as plt
from herotools.lib.position import Position
from StaticAnalysis.replays.Position import get_unique_replayids, add_replay_positions, pos_team_whole, get_lane_info


test_replay = 8839193447
timelimit = 60*7

parsed_ids = get_unique_replayids(session)
# p = add_replay_positions(session, test_replay, timelimit)
# print(p)
# get_unique_replayids(session)

query = select(distinct(Replay.replayID))
parsed_replays = set(session.scalars(query))

for r_id in parsed_replays - parsed_ids:
    add_replay_positions(session, r_id, timelimit)
session.commit()