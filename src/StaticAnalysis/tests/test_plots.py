import matplotlib.pyplot as plt
import numpy as np

import SummaryStatistics as sstat
from analysis.visualisation import (dataframe_xy, dataframe_xy_time,
                                    plot_map_points, plot_player_heroes,
                                    plot_player_positioning,
                                    plot_object_position,
                                    dataframe_xy_time_smoke,
                                    plot_object_position_scatter,
                                    plot_draft_summary,
                                    plot_pick_pairs, plot_pick_context,
                                    plot_hero_winrates, plot_runes)
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Player import PlayerStatus
from replays.Ward import Ward
from replays.Scan import Scan
from replays.Smoke import Smoke
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from pandas import cut as data_cut
from os import environ as environment
from herotools.HeroTools import heroShortName

# picks = sstat.test_player_picks()
# fig, extra = plot_player_heroes(picks)
# fig.tight_layout(h_pad=3.0)
# fig.savefig('PlayerPicks.png',
#             bbox_extra_artists=extra,
#             bbox_inches='tight')

p5_pos = sstat.test_player_position()

dire_ancient_filter = location_filter(dire_ancient_cords, PlayerStatus)
radiant_ancient_filter = location_filter(radiant_ancient_cords, PlayerStatus)
# plot_player_positioning(dataframe_xy(p5_pos[0], PlayerStatus, sstat.session))

p5_dire_filt = p5_pos[0].filter(dire_ancient_filter)
p5_radiant_filt = p5_pos[1].filter(radiant_ancient_filter)

# plot_player_positioning(dataframe_xy(p5_dire_filt, PlayerStatus, sstat.session))

wards = sstat.test_wards()
ward_df = dataframe_xy_time(wards[0], Ward, sstat.session)
# plot_object_position(ward_df)

scans = sstat.test_scans()
scans_df = dataframe_xy_time(scans[0], Scan, sstat.session)
# plot_object_position_scatter(scans_df)
# plot_object_position(scans_df)

smokes = sstat.test_smokes()
smokes_df = dataframe_xy_time_smoke(smokes[0], Smoke, sstat.session)
# plot_object_position(smokes_df, bins=16)

draft_summary = sstat.test_draft_summary()
# plot_draft_summary(draft_summary[0], draft_summary[1])

pairs = sstat.test_pairs()
_, ea_pairs = plot_pick_pairs(pairs)

# plot_pick_context(draft_summary[0],
#                   sstat.Teams['Mad Lads'],
#                   sstat.r_query)


hero_win_rate = sstat.test_hero_winrate()
# Rename index to nicknames
plot_hero_winrates(hero_win_rate)

rune_df = sstat.test_runes()
plot_runes(rune_df, sstat.Teams['Mad Lads'])