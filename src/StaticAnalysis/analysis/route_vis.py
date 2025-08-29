from typing import Tuple

import matplotlib.patheffects as PathEffects
from PIL.Image import open as Image_open

import StaticAnalysis
from StaticAnalysis import LOG
from StaticAnalysis.analysis.draft_vis import process_team_portrait, process_team_picks
from StaticAnalysis.analysis.visualisation import dataframe_xy
from StaticAnalysis.analysis.ward_vis import (build_ward_table, colour_list,
                                              plot_image_scatter)
from StaticAnalysis.analysis.smoke_vis import build_smoke_table, plot_smoke_scatter, plot_circle_scatter
from StaticAnalysis.lib.Common import (
    add_map, get_player_name, EXTENT, seconds_to_nice, get_player_name_simple, decorate_pos_estimate)
from StaticAnalysis.lib.team_info import TeamInfo, get_team
from StaticAnalysis.replays.Player import Player, PlayerStatus, Kills, Deaths
from StaticAnalysis.lib.metadata import has_picks
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Ward import Ward, WardType
from StaticAnalysis.replays.Smoke import Smoke
from StaticAnalysis.replays.Rune import Rune, RuneID
from pandas import read_sql
from matplotlib.colors import to_rgba
from herotools.util import convert_to_32_bit
from herotools.location import get_player_location
from StaticAnalysis.analysis.smoke_vis import get_smoke_time_info
from typing import List
from pandas import DataFrame
from matplotlib.axes import Axes
from sqlalchemy.orm import Session

def plot_player_paths(paths, colours, names, axis, smoke_alpha=0.3, max_time=None, min_time=None):
    # if max_time is not None:
    #     paths = [
    #         df.loc[df['game_time'] <= max_time] for df in paths
    #     ]
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
        row_filter = None
        if min_time is not None and max_time is not None:
            path = path.loc[path['game_time'].between(min_time, max_time)].copy()
        elif min_time is not None:
            path = path.loc[path['game_time'] >= min_time].copy()
        elif max_time is not None:
            path = path.loc[path['game_time'] <= max_time].copy()
        if path.empty:
            continue
        x = path['xCoordinate'].to_numpy()
        y = path['yCoordinate'].to_numpy()
        alpha_color = to_rgba(colour, smoke_alpha)
        path.loc[:,'face'] = path.loc[:,'is_smoked'].apply(
            lambda x: alpha_color if x else colour
        )
        path.loc[:,'edge'] = [colour]*path.shape[0]

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
    replay: Replay, side: Team, session, smoke_alpha=0.5,
    min_time: int = None, max_time: int = 45
    ):
    # Pregame player positions
    positions = []
    player: Player
    for player in replay.players:
        if player.team != side:
            continue
        # Note to future self: You can not filter the players list like this as it is not lazy.
        if min_time is not None and max_time is not None:
            # .between() is inclusive
            query = player.status.filter(
                PlayerStatus.game_time.between(min_time, max_time)
                )
        elif min_time is not None:
            query = player.status.filter(
                PlayerStatus.game_time >= min_time
                )
        elif max_time is not None:
            query = player.status.filter(
                PlayerStatus.game_time <= max_time
                )
        # p_df = dataframe_xy(player.status.filter(PlayerStatus.game_time <= 0),
        #                     PlayerStatus, session)
        sql_query = query.with_entities(
            PlayerStatus.xCoordinate,
            PlayerStatus.yCoordinate,
            PlayerStatus.is_smoked,
            PlayerStatus.game_time,
            PlayerStatus.is_alive).statement

        p_df = read_sql(sql_query, session.bind)
        if p_df.empty:
            continue
        # p_df['alpha'] = p_df['is_smoked'].replace({True:smoke_alpha, False:1})
        p_df['alpha'] = p_df['is_smoked'].apply(
            lambda x: smoke_alpha if x else 1.0
            )
        # p_df['face'] = p_df['is_smoked'].replace({True:alpha_color, False:1})

        # p_df['location'] = p_df.apply(
        # lambda x: get_player_location(x['xCoordinate'], x['yCoordinate']),
        # axis=1
        # )

        positions.append(p_df)

    return positions


def plot_highlighted_path(
    positions: List[DataFrame], ax_in: Axes,
    xcoord_name = 'xCoordinate', ycoord_name = 'yCoordinate',
    alpha=0.5):
    for p in positions:
        ax_in.plot(
            p[xcoord_name], p[ycoord_name],
            alpha=alpha, zorder=2, c='white', linewidth=6)

    return


def plot_highlighted_smoke_path(
    positions: List[DataFrame], time_cut: int, ax_in: Axes, alpha=0.5
    ):
    positions = [
        df[df['is_smoked'] & (df['game_time'] <= time_cut)] for df in positions
    ]

    return plot_highlighted_path(positions, ax_in, alpha=alpha)


def plot_highlighted_smoke_path_general(
    positions: List[DataFrame], min_time: int, max_time, ax_in: Axes, alpha=0.5
    ):
    positions = [
        df[df['is_smoked'] & (df['game_time'].between(min_time, max_time))] for df in positions
    ]

    return plot_highlighted_path(positions, ax_in, alpha=alpha)


def add_smoke_start_highlight(
    data: DataFrame, ax_in: Axes, font_size=12, time_col = 'Start time'
    ):
    if data.empty:
        # No smokes!
        return

    plot_circle_scatter(data, ax_in)

    time = seconds_to_nice(data[time_col][0])
    ax_in.text(
        s=time,
        x=data['averageXCoordinateStart'][0], y=data['averageYCoordinateStart'][0],
        ha='center', va='center', zorder=5,
        path_effects=[PathEffects.withStroke(linewidth=3,foreground="w")],
        color='black')

    return


def add_nice_time(x, y, ax_in: Axes, time, font_size=12):
    time = seconds_to_nice(time)
    ax_in.text(
        s=time,
        x=x, y=y,
        ha='center', va='center', zorder=5,
        path_effects=[PathEffects.withStroke(linewidth=3,foreground="w")],
        color='black')
    
    return


def add_drafts_simple(replay: Replay, team_session: Session, ax_in: Axes) -> Axes:
    dire_team = get_team(replay.dire_id)
    dire_heroes = [
        p.hero for _, p in sorted(decorate_pos_estimate(replay, Team.DIRE, dire_team))]
    dire_line = process_team_picks(dire_heroes)
    
    radiant_team =get_team(replay.radiant_id)
    radiant_heroes = [
        p.hero for _, p in sorted(decorate_pos_estimate(replay, Team.RADIANT, radiant_team))]
    radiant_line = process_team_picks(radiant_heroes)
    

    rad_axis = ax_in.inset_axes(
        bounds=[0, -0.125, 1.0, 0.1]
    )
    rad_axis.imshow(radiant_line)
    rad_axis.axis('off')
 
    dire_axis = ax_in.inset_axes(
        bounds=[0.0, 1.0, 1.0, 0.1]
    )
    dire_axis.imshow(dire_line)
    dire_axis.axis('off')

    return ax_in


def add_drafts(replay: Replay, ax_in: Axes):
    for t in replay.teams:
        if t.team == Team.RADIANT:
            radiant_line = process_team_portrait(replay, t, spacing=2)
        else:
            dire_line = process_team_portrait(replay, t, spacing=2)

    rad_axis = ax_in.inset_axes(
        bounds=[0, -0.11, 1.0, 0.1]
    )
    rad_axis.imshow(radiant_line)
    rad_axis.axis('off')
 
    dire_axis = ax_in.inset_axes(
        bounds=[0.0, 1.0, 1.0, 0.1]
    )
    dire_axis.imshow(dire_line)
    dire_axis.axis('off')

    return


def make_summary(
    replay: Replay, session: Session,
    min_time: int = None, max_time: int = None,
    bounty_grace: int = 30) -> dict:
    team_map = {p.steamID:p.team for p in replay.players}
    kills = {Team.DIRE: 0, Team.RADIANT: 0}
    deaths = {Team.DIRE: 0, Team.RADIANT: 0}
    bounties = {Team.DIRE: 0, Team.RADIANT: 0}
    first_blood = {Team.DIRE: 'no', Team.RADIANT: 'no'}
    
    # Setup the time filters
    if min_time is not None and max_time is not None:
        k_time = Kills.game_time.between(min_time, max_time)
        d_time = Deaths.game_time.between(min_time, max_time)
        r_time = Rune.game_time.between(min_time, max_time + bounty_grace)
    elif max_time is not None:
        k_time = Kills.game_time <= max_time
        d_time = Deaths.game_time <= max_time
        r_time = Rune.game_time <= max_time  + bounty_grace
    elif min_time is not None:
        k_time = Kills.game_time >= min_time
        d_time = Deaths.game_time >= min_time
        r_time = Rune.game_time >= min_time
    else:
        LOG.error("Invalid min and max time %s %s" % min_time, max_time)
        raise ValueError("One or both of min_time and max_time must be specified.")


    kill_query = session.query(Kills).filter(
        Kills.replay_ID == replay.replayID, k_time
    )
    kill: Kills
    is_first = True
    for kill in kill_query:
        if is_first:
            first_blood[team_map[kill.steam_ID]] = 'yes'
            is_first = False
        kills[team_map[kill.steam_ID]] += 1

    death_query = session.query(Deaths).filter(
        Deaths.replay_ID == replay.replayID, d_time
    )
    death: Deaths
    for death in death_query:
        deaths[team_map[death.steam_ID]] += 1

    rune_query = session.query(Rune).filter(
        Rune.replayID == replay.replayID, r_time,
        Rune.runeType == RuneID.Bounty
    )
    bounty: Rune
    for bounty in rune_query:
        bounties[bounty.team] += 1
        
    output = {
        Team.DIRE: f'''Kills: {kills[Team.DIRE]}, Deaths: {deaths[Team.DIRE]}, Bounties: {bounties[Team.DIRE]}, Drew First Blood: {first_blood[Team.DIRE]}''',
        Team.RADIANT: f'''Kills: {kills[Team.RADIANT]}, Deaths: {deaths[Team.RADIANT]}, Bounties: {bounties[Team.RADIANT]}, Drew First Blood: {first_blood[Team.RADIANT]}''',
    }
    
    return output


def plot_pregame_players(replay: Replay, team: TeamInfo, side: Team,
                         session, team_session,
                         fig, ward_size: Tuple[int, int] = (24, 21), smoke_alpha=1.0):

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
            LOG.debug(f"[PreGame] Player {player.steamID} ({convert_to_32_bit(player.steamID)}) not found in {replay.replayID}")
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

    plot_player_paths(positions, colours, names, axis, smoke_alpha=smoke_alpha, max_time=0)
    if side == Team.DIRE:
        leg = axis.legend(loc='lower left', frameon=True)
    else:
        leg = axis.legend(loc='upper right', frameon=True)

    for lh in leg.legend_handles:
        # Just using set_alpha throws an exception, may be fixed later.
        r, g, b, _ = lh.get_facecolor()
        lh.set_facecolor((r, g, b, 1.0))
    # Add smoke highlights
    plot_highlighted_smoke_path(positions, time_cut=0, ax_in=axis)
    # Wards
    wards = replay.wards.filter(Ward.game_time < 0).filter(Ward.team == side)

    # Draw lines from players to wards
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
                    LOG.warning("Ward is an obs ward!")
                    raise
                continue

            axis.plot((x1, x2), (y1, y2), color=colour, linestyle='--')
        else:
            LOG.error(f"Failed to find player for ward {x1}, {y1} at {t}")

    data = build_ward_table(wards, session, team_session, team)

    w_icons = {
        WardType.OBSERVER: Image_open(StaticAnalysis.CONFIG['images']['icons']['WARD_ICON']),
        WardType.SENTRY: Image_open(StaticAnalysis.CONFIG['images']['icons']['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, session, team_session, team)
        if data.empty and w_type == WardType.OBSERVER:
            LOG.warning(f"Ward table for {w_type} empty!")
            continue
        w_icon = w_icons[w_type]
        w_icon.thumbnail(ward_size)
        plot_image_scatter(data, axis, w_icon)

    # Smoke Icon and time
    smokes = replay.smoke_summary.filter(Smoke.game_start_time < 0).filter(Smoke.team == side)
    smoke_circle = build_smoke_table(smokes, session)
    # plot_smoke_scatter(smoke_table, axis)
    # Smoke table if wanted!
    smoke_table = get_smoke_time_info(positions)
    add_smoke_start_highlight(smoke_table, axis)
    # smoke_table['Start time'] = smoke_table['Start time'].apply(lambda x: seconds_to_nice(x))
    # axis.table(
    #     cellText = smoke_table[['Start time', 'Start location', 'End location']].to_numpy(),
    #     loc='bottom',
    #     colWidths=[0.1, 0.2, 0.2,],
    #     colLabels=["Time", "Start Location", "End Location",]
    # )
    if has_picks(session, replay):
        add_drafts_simple(replay, team_session, axis)

    # Replay ID Text
    axis.text(s=str(replay.replayID), x=0, y=1.0,
              ha='left', va='top', zorder=5,
              path_effects=[PathEffects.withStroke(linewidth=3,
                            foreground="w")],
              color='black',
              transform=axis.transAxes)

    axis.patch.set_edgecolor('black')
    axis.patch.set_linewidth('1')
    
    # Summary line
    summary_dict = make_summary(
        replay, session, min_time=None, max_time=0,
        bounty_grace=30
    )
    axis.text(s=summary_dict[side], x=0, y=-0.005,
              ha='left', va='top', zorder=5,
            #   path_effects=[PathEffects.withStroke(linewidth=3,
            #                 foreground="w")],
              color='black',
              transform=axis.transAxes)
    # Death locations
    summary_table = get_summary_table(
        replay, session,
        max_time=0, stat=Deaths, team_session=team_session
    )
    if not summary_table.empty:
        summary_table['colour'] = summary_table['team'].map(
            {Team.DIRE: 'red', Team.RADIANT:'green'}
        )
        axis.scatter(
            x=summary_table['xCoordinate'], y=summary_table['yCoordinate'],
            c=summary_table['colour'], s=100, zorder=5, marker='X', edgecolors='black'
        )
    # Team names
    dire_name = replay.get_nice_side_name(Team.DIRE)
    radiant_name = replay.get_nice_side_name(Team.RADIANT)
    # Radiant
    axis.text(0.0, 0.0, radiant_name,
        horizontalalignment='right',
        verticalalignment='bottom',
        rotation='vertical',
        transform=axis.transAxes, size=16)
    # Dire
    axis.text(1.0, 1.0, dire_name,
        horizontalalignment='left',
        verticalalignment='top',
        rotation=270,
        transform=axis.transAxes, size=16)

    return axis


def get_summary_table(
    replay: Replay, session: Session, max_time: int, stat: type, team_session: Session
    ) -> DataFrame:
    def _player_pos_dict(row, player_map) -> dict:
        p: Player
        p = player_map[row.steam_ID]
        x = p.get_position_at(row.game_time).xCoordinate
        y = p.get_position_at(row.game_time).yCoordinate
        return {'xCoordinate': x, 'yCoordinate': y}
    stat_query = session.query(stat.game_time, stat.steam_ID).filter(
        stat.replay_ID == replay.replayID, stat.game_time <= max_time)
    stat_df = read_sql(stat_query.statement, session.bind)
    # Add Player name
    name_mapper = lambda x: get_player_name_simple(x, team_session)
    stat_df['name'] = stat_df['steam_ID'].map(name_mapper)
    # Add playher team
    team_map = {p.steamID:p.team for p in replay.players}
    stat_df['team'] = stat_df['steam_ID'].map(team_map)
    # Get player positions
    if not stat_df.empty:
        player_map = {p.steamID:p for p in replay.players}
        stat_df[['xCoordinate', 'yCoordinate']] = stat_df.apply(
            lambda x: _player_pos_dict(x, player_map), axis=1, result_type='expand')

    return stat_df


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
        WardType.OBSERVER: Image_open(StaticAnalysis.CONFIG['images']['icons']['WARD_ICON']),
        WardType.SENTRY: Image_open(StaticAnalysis.CONFIG['images']['icons']['SENTRY_ICON'])
    }
    for w_type in (WardType):
        w = wards.filter(Ward.ward_type == w_type)
        data = build_ward_table(w, session, team_session, team)
        if data.empty and w_type == WardType.OBSERVER:
            LOG.warning(f"Ward table for {w_type} empty!")
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