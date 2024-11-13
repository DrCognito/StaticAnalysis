from typing import Tuple

import matplotlib.patheffects as PathEffects
from PIL.Image import open as Image_open

import StaticAnalysis
from StaticAnalysis.analysis.visualisation import dataframe_xy
from StaticAnalysis.analysis.ward_vis import (build_ward_table, colour_list,
                                              plot_image_scatter)
from StaticAnalysis.analysis.smoke_vis import build_smoke_table, plot_smoke_scatter, plot_circle_scatter
from StaticAnalysis.lib.Common import add_map, get_player_name, EXTENT, seconds_to_nice
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Player import Player, PlayerStatus
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Ward import Ward, WardType
from StaticAnalysis.replays.Smoke import Smoke
from pandas import read_sql
from matplotlib.colors import to_rgba
from herotools.util import convert_to_32_bit
from herotools.location import get_player_location
from StaticAnalysis.analysis.smoke_vis import get_smoke_time_info

def plot_player_paths(paths, colours, names, axis, smoke_alpha=0.3, max_time=None):
    if max_time is not None:
        paths = [
            df[df['game_time'] <= max_time] for df in paths
        ]
    assert(len(paths) <= len(colours))
    quiveropts = dict(
        # edgecolor=(1,1,1,1),
        #headlength=0,
        #pivot='middle',
        linewidth=1,
        # width=.05,
        # headwidth=1
        )
    # add_map(axis)
    plots = []
    for colour, path, name in zip(colours, paths, names):
        if path.empty:
            continue
        x = path['xCoordinate'].to_numpy()
        y = path['yCoordinate'].to_numpy()
        alpha_color = to_rgba(colour, smoke_alpha)
        path['face'] = path['is_smoked'].apply(
            lambda x: alpha_color if x else colour
        )
        path['edge'] = [colour]*path.shape[0]

        plot = axis.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1],
                           scale_units='xy', angles='xy', scale=1,
                           zorder=2, color=path['face'], label=name,
                        #    alpha=path['alpha'],
                            edgecolor=path['edge'],
                           **quiveropts)
        plots.append(plot)
        axis.axis('off')
    xMin, xMax, yMin, yMax = EXTENT
    axis.set_xlim(xMin, xMax)
    axis.set_ylim(yMin, yMax)

    return plots


def get_player_dataframes(
    replay: Replay, side: Team, session, smoke_alpha=0.5
    ):
    # Pregame player positions
    positions = []
    player: Player
    for player in replay.players:
        if player.team != side:
            continue
        # Note to future self: You can not filter the players list like this as it is not lazy.
        query = player.status.filter(PlayerStatus.game_time <= 45)
        # p_df = dataframe_xy(player.status.filter(PlayerStatus.game_time <= 0),
        #                     PlayerStatus, session)
        sql_query = query.with_entities(
            PlayerStatus.xCoordinate,
            PlayerStatus.yCoordinate,
            PlayerStatus.is_smoked,
            PlayerStatus.game_time,
            PlayerStatus.is_alive).statement

        p_df = read_sql(sql_query, session.bind)
        # p_df['alpha'] = p_df['is_smoked'].replace({True:smoke_alpha, False:1})
        p_df['alpha'] = p_df['is_smoked'].apply(
            lambda x: smoke_alpha if x else 1.0
            )
        # p_df['face'] = p_df['is_smoked'].replace({True:alpha_color, False:1})

        p_df['location'] = p_df.apply(
        lambda x: get_player_location(x['xCoordinate'], x['yCoordinate']),
        axis=1
        )

        positions.append(p_df)

    return positions

def plot_pregame_players(replay: Replay, team: TeamInfo, side: Team,
                         session, team_session,
                         fig, ward_size: Tuple[int, int] = (8, 7), smoke_alpha=0.5):

    axis = fig.subplots()
    # Add the map
    add_map(axis, extent=EXTENT)
    player_list = [p.name for p in team.players]
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
            name = get_player_name(team_session, player.steamID, team)
            order.append(player_list.index(name))
        except ValueError:
            name = player.steamID
            print(f"Player {player.steamID} ({convert_to_32_bit(player.steamID)})not found in {replay.replayID}")
            order.append(-1*player.steamID)

        names.append(name)
        colour_cache[player.steamID] = colour_list[iColour]
        iColour += 1

    positions = get_player_dataframes(
        replay, side, session, smoke_alpha
    )
    # Change the order to make it consistent
    positions = [p for _, p in sorted(zip(order, positions))]
    names = [n for _, n in sorted(zip(order, names))]
    colours = [c for _, c in sorted(zip(order, colours))]

    plot_player_paths(positions, colours, names, axis)
    if side == Team.DIRE:
        leg = axis.legend(loc='lower left', frameon=True)
    else:
        leg = axis.legend(loc='upper right', frameon=True)

    for lh in leg.legend_handles:
        # Just using set_alpha throws an exception, may be fixed later.
        r, g, b, _ = lh.get_facecolor()
        lh.set_facecolor((r, g, b, 1.0))
    # Wards
    wards = replay.wards.filter(Ward.game_time < 0).filter(Ward.team == side)

    # Draw lines from players to wards
    for ward in wards:
        x1 = ward.xCoordinate
        y1 = ward.yCoordinate
        t = ward.time

        if ward.player is not None:
            x2 = ward.player.get_position_at(t).xCoordinate
            y2 = ward.player.get_position_at(t).yCoordinate
            try:
                colour = colour_cache[ward.player.steamID]
            except KeyError:
                usable_time = t - replay.creepSpawn
                print(f"KeyError retrieving {ward.player.steamID}")
                print(f"Replay {replay.replayID}, side {ward.player.team} vs {ward.team}")
                print(f"At {t} ({usable_time}), {x1}, {y1}, type: {ward.ward_type}")
                print(f"Colour cache:{colour_cache}")
                if ward.ward_type == WardType.OBSERVER:
                    print("Ward is an obs ward!")
                    raise
                continue

            axis.plot((x1, x2), (y1, y2), color=colour, linestyle='--')
        else:
            print(f"Failed to find player for ward {x1}, {y1} at {t}")

    data = build_ward_table(wards, session, team_session, team)

    w_icons = {
        WardType.OBSERVER: Image_open(StaticAnalysis.CONFIG['images']['icons']['WARD_ICON']),
        WardType.SENTRY: Image_open(StaticAnalysis.CONFIG['images']['icons']['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, session, team_session, team)
        if data.empty and w_type == WardType.OBSERVER:
            # print(f"Ward table for {w_type} empty!")
            continue
        w_icon = w_icons[w_type]
        w_icon.thumbnail(ward_size)
        plot_image_scatter(data, axis, w_icon)

    # Smoke Icon
    smokes = replay.smoke_summary.filter(Smoke.game_start_time < 0).filter(Smoke.team == side)
    smoke_circle = build_smoke_table(smokes, session)
    # plot_smoke_scatter(smoke_table, axis)
    plot_circle_scatter(smoke_circle, axis)
    # Smoke table
    smoke_table = get_smoke_time_info(positions)
    print(smoke_table)
    smoke_table['Start time'] = smoke_table['Start time'].apply(lambda x: seconds_to_nice(x))
    axis.table(
        cellText = smoke_table[['Start time', 'Start location', 'End location']].to_numpy(),
        loc='bottom',
        colWidths=[0.1, 0.2, 0.2,],
        colLabels=["Time", "Start Location", "End Location",]
    )

    # Replay ID Text
    axis.text(s=str(replay.replayID), x=0, y=1.0,
              ha='left', va='top', zorder=5,
              path_effects=[PathEffects.withStroke(linewidth=3,
                            foreground="w")],
              color='black',
              transform=axis.transAxes)

    axis.patch.set_edgecolor('black')
    axis.patch.set_linewidth('1')

    return axis


# def plot_pregame_sing(replay: Replay, team: TeamInfo,
#                       session, team_session,
#                       fig, pos, ward_size: Tuple[int, int] = (8, 7),
#                       time_range=(-120, 0)):
def plot_pregame_sing(replay: Replay, team: TeamInfo,
                      session, team_session,
                      axis, pos, time_range=(-120, 0)):
    ward_size: Tuple[int, int] = (8, 7)

    # Add the map
    add_map(axis, extent=EXTENT)
    player_list = [p.name for p in team.players]
    # Pregame player positions
    positions = []
    names = []
    colour_cache = {}
    iColour = 0
    order = []
    colours = colour_list
    p_name = team.players[pos].name
    steam_id = team.players[pos].player_id
    player: Player
    for player in replay.players:
        if player.steamID != steam_id:
            continue
        side = player.team
        p_df = dataframe_xy(player.status.filter(PlayerStatus.game_time > time_range[0],
                                                 PlayerStatus.game_time <= time_range[1]),
                            PlayerStatus, session)

    # Change the order to make it consistent
    positions = [p_df, ]
    names = [p_name]
    colours = [colour_list[pos]]
    colour_cache[steam_id] = colour_list[pos]

    plot_player_paths(positions, colours, names, axis)
    if side == Team.DIRE:
        leg = axis.legend(loc='lower left', frameon=True)
    else:
        leg = axis.legend(loc='upper right', frameon=True)

    for lh in leg.legendHandles: 
        lh._legmarker.set_alpha(1)

    # Wards
    wards = replay.wards.filter(Ward.game_time < 0).filter(Ward.steamID == steam_id)

    # Draw lines from players to wards
    for ward in wards:
        x1 = ward.xCoordinate
        y1 = ward.yCoordinate
        t = ward.time

        if ward.player is not None:
            x2 = ward.player.get_position_at(t).xCoordinate
            y2 = ward.player.get_position_at(t).yCoordinate
            try:
                colour = colour_cache[ward.player.steamID]
            except KeyError:
                usable_time = t - replay.creepSpawn
                print(f"KeyError retrieving {ward.player.steamID}")
                print(f"Replay {replay.replayID}, side {ward.player.team} vs {ward.team}")
                print(f"At {t} ({usable_time}), {x1}, {y1}, type: {ward.ward_type}")
                print(f"Colour cache:{colour_cache}")
                if ward.ward_type == WardType.OBSERVER:
                    print("Ward is an obs ward!")
                    raise
                continue

            axis.plot((x1, x2), (y1, y2), color=colour, linestyle='--')
        else:
            print(f"Failed to find player for ward {x1}, {y1} at {t}")

    data = build_ward_table(wards, session, team_session, team)

    w_icons = {
        WardType.OBSERVER: Image_open(StaticAnalysis.CONFIG['images']['icons']['WARD_ICON']),
        WardType.SENTRY: Image_open(StaticAnalysis.CONFIG['images']['icons']['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, session, team_session, team)
        if data.empty and w_type == WardType.OBSERVER:
            # print(f"Ward table for {w_type} empty!")
            continue
        w_icon = w_icons[w_type]
        w_icon.thumbnail(ward_size)
        plot_image_scatter(data, axis, w_icon)

    # Replay ID Text
    axis.text(s=str(replay.replayID), x=0, y=1.0,
              ha='left', va='top', zorder=5,
              path_effects=[PathEffects.withStroke(linewidth=3,
                            foreground="w")],
              color='black',
              transform=axis.transAxes)

    axis.patch.set_edgecolor('black')
    axis.patch.set_linewidth('1')
    # xMin, xMax, yMin, yMax = EXTENT
    # axis.set_xlim(xMin, xMax)
    # axis.set_xlim(yMin, yMax)

    return axis