from StaticAnalysis.snippets.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Player import Player, NetWorth, PlayerStatus
from StaticAnalysis.analysis.Player import player_positioning_replay, closest_tower
from StaticAnalysis.lib.Common import dire_towers, radiant_towers
from sqlalchemy import select
from pandas import DataFrame, read_sql
import pandas as pd
from StaticAnalysis.analysis.networth import (
    get_lane_results, plot_networth_bar, scheme_geo, scheme_log)
import matplotlib.pyplot as plt
from herotools.lib.position import Position
from StaticAnalysis.replays.Position import get_unique_replayids, add_replay_positions


test_replay = 8831470213
timelimit = 60*7

# get_unique_replayids(session)
# add_replay_positions(session, test_replay, timelimit)
# get_unique_replayids(session)