from os import environ as environment
from typing import Tuple

import matplotlib.patheffects as PathEffects
from lib.Common import add_map, get_player_name
from lib.team_info import TeamInfo
from PIL.Image import open as Image_open
from replays.Player import Player, PlayerStatus
from replays.Replay import Replay, Team
from replays.Ward import Ward, WardType

from analysis.visualisation import dataframe_xy
from analysis.ward_vis import build_ward_table, colour_list, plot_image_scatter


def plot_player_paths(paths, colours, names, axis):
    assert(len(paths) <= len(colours))
    # add_map(axis)
    for colour, path, name in zip(colours, paths, names):
        if path.empty:
            continue
        x = path['xCoordinate'].to_numpy()
        y = path['yCoordinate'].to_numpy()

        axis.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1],
                    scale_units='xy', angles='xy', scale=1,
                    zorder=2, color=colour, label=name)
        axis.axis('off')
    axis.set_ylim(0, 1)
    axis.set_xlim(0, 1)


def plot_pregame_players(replay: Replay, team: TeamInfo, side: Team,
                         session, team_session,
                         fig, ward_size: Tuple[int, int] = (8, 7)):

    axis = fig.subplots()
    # Add the map
    add_map(axis)
    player_list = [p.name for p in team.players]
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
            name = get_player_name(team_session, player.steamID, team)
            order.append(player_list.index(name))
        except ValueError:
            name = player.steamID
            print(f"Player {player.steamID} not found in {replay.replayID}")
            order.append(-1*player.steamID)
        p_df = dataframe_xy(player.status.filter(PlayerStatus.game_time <= 0),
                            PlayerStatus, session)
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
        WardType.OBSERVER: Image_open(environment['WARD_ICON']),
        WardType.SENTRY: Image_open(environment['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, session, team_session, team)
        if data.empty and w_type == WardType.OBSERVER:
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

    return axis
