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
from matplotlib.patches import Rectangle
from sqlalchemy import and_, or_
from pandas import concat, read_sql
import numpy as np
from functools import partial


mag_x = EXTENT[1] - EXTENT[0]
mag_y = EXTENT[3] - EXTENT[2]
# Drawing area
top_left = Rectangle(
    xy=(EXTENT[0], EXTENT[2] + 0.75*mag_y),
    width = mag_x*0.2,
    height = mag_y*0.2,
    alpha=0.5
)
bottom_right = Rectangle(
    xy=(EXTENT[0] + 0.76*mag_x, EXTENT[2]),
    width = mag_x*0.2,
    height = mag_y*0.2,
    alpha=0.5
)

# Ward sample area
top_left_wards = Rectangle(
    xy=(EXTENT[0], EXTENT[2] + 0.8*mag_y),
    width = mag_x*0.15,
    height = mag_y*0.15,
    alpha=0.5
)
bottom_right_wards = Rectangle(
    xy=(EXTENT[0] + 0.81*mag_x, EXTENT[2]),
    width = mag_x*0.15,
    height = mag_y*0.15,
    alpha=0.5
)
# Filter for the tormentor corners
bottom_right_filter = and_(
    Ward.xCoordinate >= bottom_right_wards.get_x(),
    Ward.yCoordinate <= bottom_right_wards.get_y() + bottom_right_wards.get_height()
)
top_left_filter = and_(
    Ward.xCoordinate <= top_left_wards.get_x() + top_left_wards.get_width(),
    Ward.yCoordinate >= top_left_wards.get_y()
)
tormie_corners = or_(
    top_left_filter,
    bottom_right_filter
    )


def _get_mesh(rect: Rectangle, bins: int):
    '''
    Cut up a patch Rectangle ROI into n bins in x and y.
    Returns 2D arrays that map each bin in x and y (see numpy.meshgrid)
    '''
    x_dist = np.linspace(rect.get_x(), rect.get_x() + rect.get_width(), bins)
    y_dist = np.linspace(rect.get_y(), rect.get_y() + rect.get_height(), bins)
    
    return np.meshgrid(x_dist, y_dist)


def _count_within_dist(row, comparisons: DataFrame, max_dist: float):
    dist_sq = max_dist * max_dist
    total = 0
    for idx, c in comparisons.iterrows():
        dist = (c['xCoordinate'] - row['xCoordinate'])**2
        dist += (c['yCoordinate'] - row['yCoordinate'])**2
        
        if dist < dist_sq:
            total += 1
    
    return total


def heatmap(df: DataFrame, ax, 
    rect: Rectangle, bins = 100, add_scatter=True):
    # check we have data
    if df.empty:
        ax.text(0.5, 0.5, "No Data", fontsize=18,
                    horizontalalignment='center',
                    verticalalignment='center')
        ax.yaxis.set_ticks([])
        ax.xaxis.set_ticks([])
        return ax
    # Build our coordinate system and dfs
    # Note as its lower and upper bounds it should be +1 for 100x100 data displayed bins!
    coord_x, coord_y = _get_mesh(rect, bins+1)
    mesh_df = DataFrame({
    'xCoordinate': np.reshape(coord_x, (bins+1)*(bins+1)),
    'yCoordinate': np.reshape(coord_y, (bins+1)*(bins+1))
    })
    # Count our ward overlaps for each point
    # cc_t = partial(circle_counter, circles = df_t['circle'])
    dc_t = partial(_count_within_dist, comparisons=df, max_dist=1050)
    mesh_df['count'] = mesh_df.apply(dc_t, axis=1)

    # Add the maps
    add_map(ax, extent=EXTENT)
    ax.axis('off')
    # Fix the weights
    coord_z = mesh_df['count'].values.reshape(bins+1,bins+1).T
    coord_z = np.ma.masked_array(coord_z, coord_z < 1)

    # Add the colour meshes
    # These have to be transposed but I am not sure...
    ax.pcolormesh(
        coord_x.T,
        coord_y.T,
        coord_z,
        alpha=0.5)
    
    # Do the scatter if we want!
    if add_scatter:
        ax.scatter(
            x=df['xCoordinate'], y=df['yCoordinate'],
            alpha=1.0, marker='o', s=25, edgecolors='black'
        )
    # Set top axis limits
    ax.set_ylim(rect.get_y(), rect.get_y() + rect.get_height())
    ax.set_xlim(rect.get_x(), rect.get_x() + rect.get_width())
    
    return ax


def plot_tormie_sentries_heatmap(
    team: TeamInfo, r_query, fig, session
    ):
    # Filter by side to get team only wards
    d_replays = r_query.filter(Replay.get_side_filter(team, Team.DIRE)).subquery()
    r_replays = r_query.filter(Replay.get_side_filter(team, Team.RADIANT)).subquery()
    dire_wards = session.query(Ward).filter(
        Ward.team == Team.DIRE, Ward.ward_type == WardType.SENTRY
        ).join(d_replays)
    radiant_wards = session.query(Ward).filter(
        Ward.team == Team.RADIANT, Ward.ward_type == WardType.SENTRY
        ).join(r_replays)

    # Build the dfs for the corners from the team wards
    top_df = [
        read_sql(dire_wards.filter(top_left_filter).statement, session.bind),
        read_sql(radiant_wards.filter(top_left_filter).statement, session.bind)]
    try:
        top_df = concat([df for df in top_df if not df.empty], ignore_index=True)
    except ValueError:
        top_df = DataFrame()
    bottom_df = [
        read_sql(dire_wards.filter(bottom_right_filter).statement, session.bind),
        read_sql(radiant_wards.filter(bottom_right_filter).statement, session.bind)
    ]
    try:
        bottom_df = concat([df for df in bottom_df if not df.empty], ignore_index=True)
    except ValueError:
        bottom_df = DataFrame()

    ax_t, ax_b = fig.subplots(ncols=2)
    heatmap(top_df, ax_t, top_left, add_scatter=True)
    heatmap(bottom_df, ax_b, bottom_right, add_scatter=True)
    
    return fig


def plot_tormentor_sentries(
    team: TeamInfo, r_query, fig, session
    ):
    '''
    Plot the sentries around the tormentor as defined by the constants top_left and bottom_right.
    '''
    # Per side replays
    d_replays = r_query.filter(Replay.get_side_filter(team, Team.DIRE)).subquery()
    r_replays = r_query.filter(Replay.get_side_filter(team, Team.RADIANT)).subquery()
    # Apply ward team, type and region filters
    dire_wards = session.query(Ward).filter(
        Ward.team == Team.DIRE, Ward.ward_type == WardType.SENTRY, tormie_corners
        ).join(d_replays)
    radiant_wards = session.query(Ward).filter(
        Ward.team == Team.RADIANT, Ward.ward_type == WardType.SENTRY, tormie_corners
        ).join(r_replays)
    # Get the dataframe
    dire_df = read_sql(dire_wards.statement, session.bind)
    radiant_df = read_sql(radiant_wards.statement, session.bind)
    combined_df = concat((radiant_df, dire_df), ignore_index=True)
    # Fig setup
    ax_t, ax_b = fig.subplots(ncols=2)
    # fig.set_size_inches(8, 4)
    # Add the maps
    add_map(ax_t, extent=EXTENT)
    ax_t.axis('off')
    add_map(ax_b, extent=EXTENT)
    ax_b.axis('off')
    # Plot the combined df scatter
    ax_t.scatter(
        x=combined_df['xCoordinate'], y=combined_df['yCoordinate'],
        alpha=1.0, marker='o', s=50, edgecolors='black'
    )
    ax_b.scatter(
        x=combined_df['xCoordinate'], y=combined_df['yCoordinate'],
        alpha=1.0, marker='o', s=50, edgecolors='black'
    )
    # Set top axis limits
    ax_t.set_ylim(top_left.get_y(), top_left.get_y() + top_left.get_height())
    ax_t.set_xlim(top_left.get_x(), top_left.get_x() + top_left.get_width())
    # Set bottom axis limits
    ax_b.set_ylim(bottom_right.get_y(), bottom_right.get_y() + bottom_right.get_height())
    ax_b.set_xlim(bottom_right.get_x(), bottom_right.get_x() + bottom_right.get_width())
    
    return fig


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
            t = ward.game_time

            if ward.player is not None:
                x2 = ward.player.get_position_at(t).xCoordinate
                y2 = ward.player.get_position_at(t).yCoordinate
                try:
                    colour = colour_cache[ward.player.steamID]
                except KeyError:
                    usable_time = t
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