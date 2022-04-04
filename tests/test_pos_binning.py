import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.minimal_db as db
from analysis.Player import (cumulative_player, pick_context, player_heroes,
                             player_position)
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from replays.Player import PlayerStatus
from analysis.visualisation import dataframe_xy, get_binning_percentile_xy

start, end = (-2*60, 10*60)
recent_limit = 5
test_pos = 0

(pos_dire, pos_dire_limited),\
            (pos_radiant, pos_radiant_limited) = player_position(db.session, db.r_query, db.team,
                                                                 player_slot=test_pos,
                                                                 start=start, end=end,
                                                                 recent_limit=recent_limit)

dire_ancient_filter = location_filter(dire_ancient_cords,
                                      PlayerStatus)
pos_dire = pos_dire.filter(dire_ancient_filter)
pos_dire_limited = pos_dire_limited.filter(dire_ancient_filter)

pos_dire_df = dataframe_xy(pos_dire, PlayerStatus, db.session)
pos_dire_limited_df = dataframe_xy(pos_dire_limited, PlayerStatus, db.session)
