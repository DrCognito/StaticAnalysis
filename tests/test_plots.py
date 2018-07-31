import matplotlib.pyplot as plt
import numpy as np

import SummaryStatistics as sstat
from analysis.visualisation import (dataframe_xy, dataframe_xy_time,
                                    plot_map_points, plot_player_heroes,
                                    plot_player_positioning)
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Player import PlayerStatus
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from pandas import cut as data_cut
from os import environ as environment

# picks = sstat.test_player_picks()
# fig, extra = plot_player_heroes(picks)
# fig.tight_layout(h_pad=3.0)
# fig.savefig('PlayerPicks.png',
#             bbox_extra_artists=extra,
#             bbox_inches='tight')

p5_pos = sstat.test_player_position()
# test_plot(p5_pos[0])
# test_plot(p5_pos[1])

dire_ancient_filter = location_filter(dire_ancient_cords, PlayerStatus)
radiant_ancient_filter = location_filter(radiant_ancient_cords, PlayerStatus)
plot_player_positioning(dataframe_xy(p5_pos[0], PlayerStatus, sstat.session))

p5_dire_filt = p5_pos[0].filter(dire_ancient_filter)
p5_radiant_filt = p5_pos[1].filter(radiant_ancient_filter)

plot_player_positioning(dataframe_xy(p5_dire_filt, PlayerStatus, sstat.session))