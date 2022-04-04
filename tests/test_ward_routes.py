import os
import pathlib
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.minimal_db as db
from analysis.Player import (cumulative_player, pick_context, player_heroes,
                             player_position)
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from replays.Player import PlayerStatus
from analysis.visualisation import dataframe_xy, get_binning_percentile_xy
from lib.team_info import TeamInfo
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from analysis.visualisation import (dataframe_xy, dataframe_xy_time,
                                    dataframe_xy_time_smoke,
                                    plot_draft_summary, plot_hero_winrates,
                                    plot_map_points, plot_object_position,
                                    plot_object_position_scatter,
                                    plot_pick_context, plot_pick_pairs,
                                    plot_player_heroes,
                                    plot_player_positioning, plot_runes,
                                    get_binning_percentile_xy)
# from scipy.interpolate import interp2d
from os import environ as environment
from dotenv import load_dotenv
from analysis.ward_vis import colour_list

load_dotenv(dotenv_path="setup.env")

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


test_radiant_out = pathlib.Path("./tests/")
test_dire_out = pathlib.Path("./tests/")


def do_positioning(team: TeamInfo, r_query,
                   start: int, end: int,
                   update_dire=True, update_radiant=True,
                   positions=(0, 1, 2, 3, 4),
                   recent_limit=5):
    '''Make the positioning plots between start and end times for
       positions in r_query.
       update_dire and update_radiant control updating specific side.
       NOTE: Positions are zero based!
    '''

    for pos in positions:
        if pos >= len(team.players):
            print("Position {} is out of range for {}"
                  .format(pos, team.name))
        p_name = team.players[pos].name
        print("Processing {} for {}".format(p_name, team.name))
        (_, pos_dire_limited),\
            (_, pos_radiant_limited) = player_position(db.session, r_query, team,
                                                                 player_slot=pos,
                                                                 start=start, end=end,
                                                                 recent_limit=recent_limit)
        if update_dire:
            if pos_dire.count() == 0:
                print("No data for {} on Dire.".format(team.players[pos].name))
                continue
            fig, axes = plt.subplots(1, 1, figsize=(7, 10))

            output = test_dire_out / f'ward_pos_dire{pos}.jpg'
            dire_ancient_filter = location_filter(dire_ancient_cords,
                                                  PlayerStatus)
            pos_dire_limited = pos_dire_limited.filter(dire_ancient_filter)

            pos_dire_limited_df = dataframe_xy(pos_dire_limited, PlayerStatus, db.session)
            vmin, vmax = get_binning_percentile_xy(pos_dire_limited_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_dire_limited_df,
                                        bins=64, ax_in=axes,
                                        vmin=vmin, vmax=vmax)
            axis.set_title('Latest 5 games')
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            plt.close(fig)
            fig.clf()

        if update_radiant:
            if pos_radiant.count() == 0:
                print("No data for {} on Radiant.".format(team.players[pos].name))
                continue
            fig, axes = plt.subplots(1, 1, figsize=(7, 10))

            output = test_radiant_out / f'ward_pos_radiant{pos}.jpg'
            # axes = fig.subplots(1, 2)
            ancient_filter = location_filter(radiant_ancient_cords,
                                             PlayerStatus)

            pos_radiant_limited = pos_radiant_limited.filter(ancient_filter)
            pos_radiant_limited_df = dataframe_xy(pos_radiant_limited, PlayerStatus, db.session)
            vmin, vmax = get_binning_percentile_xy(pos_radiant_limited_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_radiant_limited_df,
                                        bins=64, ax_in=axes,
                                        vmin=vmin, vmax=vmax)
            axis.set_title('Latest 5 games')
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            plt.close(fig)
            fig.clf()
    # fig.clf()
    return


# do_positioning(db.team, db.r_query, start=-2*60, end=0)

def add_map(axis, origin=(0, 0)):
    img = mpimg.imread(environment['MAP_PATH'])
    extent_test = [0.005, 0.995, 0.005, 0.995]
    axis.imshow(img, extent=extent_test, zorder=0)
    # ax_in.axis('off')

    return axis

# Dire for now
def plot_player_path(team: TeamInfo, r_query, pos, start: int, end: int, filter = None):
    (_, _),\
            (positions, _) = player_position(db.session, r_query, team,
                                     player_slot=pos,
                                     start=start, end=end,
                                     recent_limit=1)

    if filter is not None:
        positions = positions.filter(filter)

    positions_df = dataframe_xy(positions, PlayerStatus, db.session)
    # positions_smooth = 

    # print(positions_df)

    return positions_df


test = plot_player_path(db.team, db.rq_dire, pos=0, start=-90, end=0)

print(test.columns)

positions = []
for p in range(0, 5):
    t = plot_player_path(db.team, db.rq_radiant, pos=p, start=-2*60, end=0)
    positions.append(t)

fig, axis = plt.subplots(1, 1, figsize=(7, 10))


def plot_player_paths(paths, colours, axis, ax_off=(0, 0)):
    assert(len(paths) <= len(colours))
    add_map(axis, ax_off)
    for colour, path in zip(colours, paths):
        x = path['xCoordinate'].to_numpy()
        y = path['yCoordinate'].to_numpy()

        axis.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1],
                    scale_units='xy', angles='xy', scale=1,
                    zorder=2, color=colour)
        axis.axis('off')

plot_player_paths(positions, colour_list, axis, (-0.02, 0))