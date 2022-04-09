import os
import pathlib
import sys
from typing import Tuple
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.minimal_db as db
from analysis.Player import (cumulative_player, pick_context, player_heroes,
                             player_position)
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from replays.Player import Player, PlayerStatus
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
import pandas as pd
from replays.Replay import Replay, Team
from analysis.Replay import (draft_summary, get_ptbase_tslice,
                             get_ptbase_tslice_side,
                             get_rune_control, get_smoke, hero_win_rate,
                             pair_rate, win_rate_table, get_side_replays,
                             counter_picks)
from replays.Ward import Ward, WardType
from analysis.ward_vis import build_ward_table, plot_image_scatter
from PIL.Image import open as Image_open
from lib.Common import seconds_to_nice, get_player_map,get_player_name
import matplotlib.patheffects as PathEffects

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

cell_size = 1/64


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

def add_map(axis, extent=[-cell_size, 1-cell_size, 0, 1]):
    img = mpimg.imread(environment['MAP_PATH'])
    # extent_test = [0.005, 0.995, 0.005, 0.995]
    axis.imshow(img, extent=extent, zorder=0)
    # ax_in.axis('off')

    return axis


def get_player_path(team: TeamInfo, r_query,
                     pos, start: int, end: int, side: Team,
                     filter=None):
    (dire, _),\
            (radiant, _) = player_position(db.session, r_query, team,
                                           player_slot=pos,
                                           start=start, end=end,
                                           recent_limit=1)
    positions = dire if side == Team.DIRE else radiant

    if filter is not None:
        positions = positions.filter(filter)

    positions_df = dataframe_xy(positions, PlayerStatus, db.session)
    # positions_smooth = 

    # print(positions_df)

    return positions_df


test = get_player_path(db.team, db.rq_dire, pos=0, start=-90, end=0, side=Team.DIRE)

print(test.columns)

positions = []
for p in range(0, 5):
    t = get_player_path(db.team, db.rq_dire, pos=p, start=-2*60, end=0, side=Team.DIRE)
    positions.append(t)

fig, axis = plt.subplots(1, 1, figsize=(7, 10))


def plot_player_paths(paths, colours, names, axis):
    assert(len(paths) <= len(colours))
    # add_map(axis)
    for colour, path, name in zip(colours, paths, names):
        x = path['xCoordinate'].to_numpy()
        y = path['yCoordinate'].to_numpy()

        axis.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1],
                    scale_units='xy', angles='xy', scale=1,
                    zorder=2, color=colour, label=name)
        axis.axis('off')
    axis.set_ylim(0, 1)
    axis.set_xlim(0, 1)


# plot_player_paths(positions, colour_list, axis)


def plot_some_wards(r_query, n_wards=4, extent=[-cell_size, 1-cell_size, 0, 1]):
    data = {
            'xCoordinate': [],
            'yCoordinate': [],
    }
    for ward, _ in zip(r_query.one().wards, range(n_wards)):
        data['xCoordinate'].append(ward.xCoordinate)
        data['yCoordinate'].append(ward.yCoordinate)

    fig, axis = plt.subplots(1, 1, figsize=(7, 10))
    axis.scatter(data['xCoordinate'], data['yCoordinate'])
    axis.set_ylim(0, 1)
    axis.set_xlim(0, 1)
    add_map(axis, extent)
    axis.axis('off')
    plt.show()
    # fig.savefig('./tests/ward_pos.png')


# plot_some_wards(db.rq_radiant)

# fig, axis = plt.subplots(1, 1, figsize=(7, 10))
# add_map(axis)
# axis.axis('off')
# fig.savefig('./tests/map_render.png')


def plot_pregame_players(replay: Replay, team: TeamInfo, side: Team,
                         axis, ward_size: Tuple[int, int] = (8, 7)):
    # Add the map
    add_map(axis)
    player_list = [p.name for p in db.team.players]
    # Pregame player positions
    positions = []
    names = []
    colour_cache = {}
    iColour = 0
    order = []
    colours = colour_list
    player: Player
    for player in replay.players:
        if player.team != side:
            continue
        try:
            name = get_player_name(db.team_session, player.steamID)
            order.append(player_list.index(name))
        except ValueError:
            name = player.steamID
            order.append(-1*player.steamID)
        p_df = dataframe_xy(player.status.filter(PlayerStatus.game_time <= 0),
                            PlayerStatus, db.session)
        positions.append(p_df)
        names.append(name)
        colour_cache[player.steamID] = colour_list[iColour]
        iColour += 1
    # Change the order to make it consistent
    positions = [p for _, p in sorted(zip(order, positions))]
    names = [n for _, n in sorted(zip(order, names))]
    colours = [c for _, c in sorted(zip(order, colours))]

    plot_player_paths(positions, colours, names, axis)
    if side == Team.DIRE:
        axis.legend(loc='lower left', frameon=True)
    else:
        axis.legend(loc='upper right', frameon=True)

    # Wards
    wards = replay.wards.filter(Ward.game_time < 0).filter(Ward.team == side)

    for ward in wards:
        x1 = ward.xCoordinate
        y1 = ward.yCoordinate
        t = ward.time

        x2 = ward.player.get_position_at(t).xCoordinate
        y2 = ward.player.get_position_at(t).yCoordinate
        colour = colour_cache[ward.player.steamID]

        axis.plot((x1, x2), (y1, y2), color=colour, linestyle='--')

    data = build_ward_table(wards, db.session, db.team_session)

    w_icons = {
        WardType.OBSERVER: Image_open(environment['WARD_ICON']),
        WardType.SENTRY: Image_open(environment['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, db.session, db.team_session)
        if data.empty:
            print(f"Ward table for {w_type} empty!")
            continue
        w_icon = w_icons[w_type]
        w_icon.thumbnail(ward_size)
        plot_image_scatter(data, axis, w_icon)

    # Replay ID Text
    axis.text(s=str(replay.replayID), x=0, y=1.0,
              ha='left', va='top', zorder=5,
              path_effects=[PathEffects.withStroke(linewidth=3,
                            foreground="w")],
              color='black')


fig, axis = plt.subplots(1, 1, figsize=(7, 7))
r = db.rq_dire.one()
plot_pregame_players(r, db.team, Team.DIRE, axis)
fig.tight_layout()
fig.savefig("./tests/route_test.jpg")
plt.show()