from StaticAnalysis import CONFIG, LOG
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.analysis.smoke_vis import build_smoke_table
from StaticAnalysis.analysis.ward_vis import (build_ward_table, colour_list,
                                              plot_image_scatter)
from StaticAnalysis.analysis.route_vis import get_player_dataframes
from StaticAnalysis.lib.Common import add_map, get_player_name, EXTENT
from StaticAnalysis.analysis.route_vis import (
    plot_player_paths, plot_highlighted_smoke_path_general,
    add_smoke_start_highlight, add_nice_time
    )
from StaticAnalysis.replays.Ward import Ward, WardType
from StaticAnalysis.replays.Smoke import Smoke
from StaticAnalysis.analysis.smoke_vis import get_smoke_time_info
from herotools.util import convert_to_32_bit

from typing import Tuple
from pandas import DataFrame
from PIL.Image import open as Image_open
import matplotlib.patheffects as PathEffects

def plot_tormentor_kill_players(
    replay: Replay, team: TeamInfo, side: Team,
    session, team_session, kill_time:int,
    tormentor_location: Tuple[float, float],
    fig, ward_size: Tuple[int, int] = (24, 21), smoke_alpha=1.0,
    time_slice: int=5*60, add_ward_lines=False, add_draft=False,
    ):

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
            LOG.debug(f"Player {player.steamID} ({convert_to_32_bit(player.steamID)}) not found in {replay.replayID}")
            order.append(-1*player.steamID)

        names.append(name)
        colour_cache[player.steamID] = colour_list[iColour]
        iColour += 1

    min_time = kill_time - time_slice
    max_time = kill_time + 45 # Allow for full smoke duration to enable table
    positions = get_player_dataframes(
        replay, side, session, smoke_alpha,
        min_time, max_time
    )
    # Change the order to make it consistent
    positions = [p for _, p in sorted(zip(order, positions))]
    names = [n for _, n in sorted(zip(order, names))]
    colours = [c for _, c in sorted(zip(order, colours))]

    plot_player_paths(positions, colours, names, axis, smoke_alpha=smoke_alpha, max_time=kill_time)
    if side == Team.DIRE:
        leg = axis.legend(loc='lower left', frameon=True)
    else:
        leg = axis.legend(loc='upper right', frameon=True)

    for lh in leg.legend_handles:
        # Just using set_alpha throws an exception, may be fixed later.
        r, g, b, _ = lh.get_facecolor()
        lh.set_facecolor((r, g, b, 1.0))
    # Add smoke highlights
    plot_highlighted_smoke_path_general(positions, min_time, max_time, ax_in=axis)
    # Wards
    wards = replay.wards.filter(Ward.game_time.between(min_time, kill_time) ).filter(Ward.team == side)

    # Draw lines from players to wards
    if add_ward_lines:
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
                    LOG.error(f"KeyError retrieving {ward.player.steamID}")
                    LOG.debug(f"Replay {replay.replayID}, side {ward.player.team} vs {ward.team}")
                    LOG.debug(f"At {t} ({usable_time}), {x1}, {y1}, type: {ward.ward_type}")
                    LOG.debug(f"Colour cache:{colour_cache}")
                    if ward.ward_type == WardType.OBSERVER:
                        LOG.error("Ward is an obs ward!")
                        raise
                    continue

                axis.plot((x1, x2), (y1, y2), color=colour, linestyle='--')
            else:
                LOG.error(f"Failed to find player for ward {x1}, {y1} at {t}")

    data = build_ward_table(wards, session, team_session, team)

    w_icons = {
        WardType.OBSERVER: Image_open(CONFIG['images']['icons']['WARD_ICON']),
        WardType.SENTRY: Image_open(CONFIG['images']['icons']['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, session, team_session, team)
        if data.empty and w_type == WardType.OBSERVER:
            LOG.debug(f"Ward table for {w_type} empty!")
            continue
        w_icon = w_icons[w_type]
        w_icon.thumbnail(ward_size)
        plot_image_scatter(data, axis, w_icon)
    font_size = 12
    kill_time_loc = (tormentor_location[0], tormentor_location[1] - 600)
    add_nice_time(*kill_time_loc, axis, kill_time, font_size=font_size)
    
    # Tormentor icon
    tormentor_icon = Image_open(CONFIG['images']['icons']['TORMENTOR_ICON'])
    tormentor_icon.thumbnail(ward_size)
    plot_image_scatter(
        DataFrame({'xCoordinate':[tormentor_location[0],], 'yCoordinate':[tormentor_location[1],]}),
        axis,
        tormentor_icon
        )

    # Smoke Icon and time
    smokes = replay.smoke_summary.filter(Smoke.game_start_time.between(min_time, kill_time)).filter(Smoke.team == side)
    smoke_circle = build_smoke_table(smokes, session)
    # plot_smoke_scatter(smoke_table, axis)
    # Smoke table if wanted!
    smoke_table = get_smoke_time_info(positions)
    add_smoke_start_highlight(smoke_table, axis)
    # print(smoke_table)
    # smoke_table['Start time'] = smoke_table['Start time'].apply(lambda x: seconds_to_nice(x))
    # axis.table(
    #     cellText = smoke_table[['Start time', 'Start location', 'End location']].to_numpy(),
    #     loc='bottom',
    #     colWidths=[0.1, 0.2, 0.2,],
    #     colLabels=["Time", "Start Location", "End Location",]
    # )
    # add_drafts(replay, axis)

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