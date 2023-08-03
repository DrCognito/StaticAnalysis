import argparse
import json
import shutil
import time as t
from argparse import ArgumentParser
from datetime import datetime, timedelta
from itertools import zip_longest
from os import environ as environment
from os import mkdir
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import pytz
from fpdf import FPDF
from herotools.important_times import ImportantTimes, nice_time_names
from matplotlib import rcParams, ticker
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas import DataFrame, IntervalIndex, cut, read_sql
from propubs.libs.vis import plot_team_pubs, plot_team_pubs_timesplit
from propubs.model.pub_heroes import InitDB as InitPubDB
from propubs.model.team_info import (BAD_TEAM_TIME_SENTINEL,
                                     get_team_last_result)
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from StaticAnalysis.analysis.draft_vis import replay_draft_image
from StaticAnalysis.analysis.Player import player_heroes, player_position, player_positioning_single
from StaticAnalysis.analysis.priority_picks import (priority_picks,
                                                    priority_picks_double)
from StaticAnalysis.analysis.Replay import (counter_picks, draft_summary,
                                            get_ptbase_tslice,
                                            get_ptbase_tslice_side,
                                            get_rune_control, get_side_replays,
                                            get_smoke, hero_win_rate,
                                            pair_rate, win_rate_table)
from StaticAnalysis.analysis.route_vis import plot_pregame_players, plot_pregame_sing
from StaticAnalysis.analysis.table_picks import create_tables
from StaticAnalysis.analysis.visualisation import (
    dataframe_xy, dataframe_xy_time, dataframe_xy_time_smoke,
    get_binning_percentile_xy, plot_draft_summary, plot_flex_picks,
    plot_hero_winrates, plot_object_position, plot_object_position_scatter,
    plot_pick_context, plot_pick_pairs, plot_player_heroes, plot_runes)
from StaticAnalysis.analysis.ward_vis import (build_ward_table,
                                              plot_drafts_above,
                                              plot_eye_scatter)
from StaticAnalysis.lib.Common import (ChainedAssignent, dire_ancient_cords,
                                       location_filter, radiant_ancient_cords)
from StaticAnalysis.lib.metadata import (has_picks, is_full_replay, is_updated,
                                         make_meta)
from StaticAnalysis.lib.team_info import InitTeamDB, TeamInfo
from StaticAnalysis.replays.Player import PlayerStatus, Player
from StaticAnalysis.replays.Replay import InitDB, Replay, Team
from StaticAnalysis.replays.Scan import Scan
from StaticAnalysis.replays.Smoke import Smoke
from StaticAnalysis.replays.TeamSelections import TeamSelections
from StaticAnalysis.replays.Ward import Ward, WardType
from StaticAnalysis.lib.team_info import TeamPlayer
from typing import List


DB_PATH = environment['PARSED_DB_PATH']
PLOT_BASE_PATH = environment['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()

pub_engine = InitPubDB()
pub_maker = sessionmaker(bind=pub_engine)
pub_session = pub_maker()


def plot_positioning(session, replay_id, team: TeamInfo,
                     steam_id: int,
                     start: int, end: int,
                     axis, fig):
    positioning = player_positioning_single(session, replay_id, team, steam_id, start, end)
    positioning_df = dataframe_xy(positioning, PlayerStatus, session)
    vmin, vmax = get_binning_percentile_xy(positioning_df)
    vmin = max(1.0, vmin)
    plot_object_position(positioning_df,
                         bins=64, fig_in=fig, ax_in=axis,
                         vmin=vmin, vmax=vmax)
    return


def player_heatmap_report(session, replay_id, team: TeamInfo,
                          custom_times=None, identifier=None):
    times = [(0,5), (5, 10), (10, 15), (15, 20)]
    if custom_times is not None:
        times = custom_times

    report_path: Path = Path(PLOT_BASE_PATH) / "REPORTS" / team.name
    report_path.mkdir(parents=True, exist_ok=True)
    if identifier is not None:
        report_output = report_path / (f'{team.name}_{replay_id}_{identifier}_heatmap.pdf')
    else:
        report_output = report_path / (f'{team.name}_{replay_id}_heatmap.pdf')
    pdf = FPDF()
    # Get individual ones
    p: TeamPlayer
    for slot, p in enumerate(team.players):
        team_path: Path = Path(PLOT_BASE_PATH) / "CUSTOM" / team.name
        team_path.mkdir(parents=True, exist_ok=True)
        p_name = p.name
        steam_id = p.player_id
        if identifier is not None:
            post_fix = f'{identifier}_heatmap.png'
        else:
            post_fix = f'heatmap.png'
        for ti in times:
            fig, axes = plt.subplots(figsize=(8.27, 11.69))
            # fig.set_dpi(200)
            plot_positioning(session, replay_id, team, steam_id,
                             start=ti[0]*60, end=ti[1]*60, axis=axes, fig=fig)
            axes.set_title(f'{ti[0]} to {ti[1]} mins')
            axes.axis('on')
            axes.set_xticks([])
            axes.set_yticks([])

            axes.set_ylabel(p_name)
            output = team_path / (f'{p_name}_{replay_id}_{ti[0]}to{ti[1]}_{post_fix}')
            fig.savefig(output, bbox_inches='tight')
            fig.clf()

            pdf.add_page()
            pdf.image(output, keep_aspect_ratio=True, w=180, h=290)

    pdf.output(report_output)


def plot_route(session, replay_id, team: TeamInfo, team_session,
               player_slot: int,
               start: int, end: int, axis):

    replay = session.query(Replay).filter(Replay.replayID == replay_id).one_or_none()
    if replay is None:
        print(f"plot_route: Replays {replay_id} not found!")
        return

    plot_pregame_sing(replay, team, session, team_session, axis, player_slot, time_range=(start, end))

    return


def player_route_report(session, replay_id, team: TeamInfo,
                        custom_times=None, identifier=None):
    times = [(0, 5), (5, 10), (10, 15), (15, 20)]
    if custom_times is not None:
        times = custom_times

    report_path: Path = Path(PLOT_BASE_PATH) / "REPORTS" / team.name
    report_path.mkdir(parents=True, exist_ok=True)
    if identifier is not None:
        report_output = report_path / (f'{team.name}_{replay_id}_{identifier}_route.pdf')
    else:
        report_output = report_path / (f'{team.name}_{replay_id}_route.pdf')
    pdf = FPDF()
    # Get individual ones
    p: TeamPlayer
    for slot, p in enumerate(team.players):
        team_path: Path = Path(PLOT_BASE_PATH) / "CUSTOM" / team.name
        team_path.mkdir(parents=True, exist_ok=True)
        p_name = p.name
        # steam_id = p.player_id
        if identifier is not None:
            post_fix = f'{identifier}_route.png'
        else:
            post_fix = f'route.png'
        for ti in times:
            fig, axes = plt.subplots(figsize=(8.27, 11.69))
            # fig.set_dpi(200)
            plot_route(session, replay_id, team, team_session, slot,
                       start=ti[0]*60, end=ti[1]*60, axis=axes)
            axes.set_title(f'{ti[0]} to {ti[1]} mins')
            axes.axis('on')
            axes.set_xticks([])
            axes.set_yticks([])

            axes.set_ylabel(p_name)
            output = team_path / (f'{p_name}_{replay_id}_{ti[0]}to{ti[1]}_{post_fix}')
            fig.savefig(output, bbox_inches='tight')
            fig.clf()

            pdf.add_page()
            pdf.image(output, keep_aspect_ratio=True, w=180, h=290)

    pdf.output(report_output)


def do_positioning(team: TeamInfo, r_query,
                   start: int, end: int,
                   metadata: dict,
                   update_dire=True, update_radiant=True,
                   positions=(0, 1, 2, 3, 4),
                   recent_limit=5):
    '''Make the positioning plots between start and end times for
       positions in r_query.
       update_dire and update_radiant control updating specific side.
       NOTE: Positions are zero based!
    '''
    if not update_dire and not update_radiant:
        return metadata
    metadata['player_names'] = []

    if update_dire:
        metadata['plot_pos_dire'] = []
    if update_radiant:
        metadata['plot_pos_radiant'] = []
    team_path: Path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)

    for pos in positions:
        if pos >= len(team.players):
            print("Position {} is out of range for {}"
                  .format(pos, team.name))
        p_name = team.players[pos].name
        metadata['player_names'].append(p_name)
        print("Processing {}({}).".format(p_name, team.name), end=" ")
        (pos_dire, pos_dire_limited),\
            (pos_radiant, pos_radiant_limited) = player_position(session, r_query, team,
                                                                 player_slot=pos,
                                                                 start=start, end=end,
                                                                 recent_limit=recent_limit)
        if update_dire:
            if pos_dire.count() == 0:
                print("No data for {} on Dire.".format(team.players[pos].name))
            fig, axes = plt.subplots(1, 2, figsize=(10, 13))

            output = team_path / 'dire' / (p_name + '.jpg')
            # dire_ancient_filter = location_filter(dire_ancient_cords,
            #                                       PlayerStatus)
            # pos_dire = pos_dire.filter(dire_ancient_filter)
            # pos_dire_limited = pos_dire_limited.filter(dire_ancient_filter)

            pos_dire_df = dataframe_xy(pos_dire, PlayerStatus, session)
            vmin, vmax = get_binning_percentile_xy(pos_dire_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_dire_df,
                                        bins=64, fig_in=fig, ax_in=axes[0],
                                        vmin=vmin, vmax=vmax)
            pos_dire_limited_df = dataframe_xy(pos_dire_limited, PlayerStatus, session)
            vmin, vmax = get_binning_percentile_xy(pos_dire_limited_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_dire_limited_df,
                                        bins=64, ax_in=axes[1],
                                        vmin=vmin, vmax=vmax)
            axis.set_title('Latest 5 games')
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata['plot_pos_dire'].append(relpath)
            fig.clf()

        if update_radiant:
            if pos_radiant.count() == 0:
                print("No data for {} on Radiant.".format(team.players[pos].name))
            fig, axes = plt.subplots(1, 2, figsize=(10, 13))

            output = team_path / 'radiant' / (p_name + '.jpg')
            # axes = fig.subplots(1, 2)
            # ancient_filter = location_filter(radiant_ancient_cords,
            #                                  PlayerStatus)
            # pos_radiant = pos_radiant.filter(ancient_filter)
            pos_radiant_df = dataframe_xy(pos_radiant, PlayerStatus, session)
            vmin, vmax = get_binning_percentile_xy(pos_radiant_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_radiant_df,
                                        bins=64, fig_in=fig, ax_in=axes[0],
                                        vmin=vmin, vmax=vmax)

            # pos_radiant_limited = pos_radiant_limited.filter(ancient_filter)
            pos_radiant_limited_df = dataframe_xy(pos_radiant_limited, PlayerStatus, session)
            vmin, vmax = get_binning_percentile_xy(pos_radiant_limited_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_radiant_limited_df,
                                        bins=64, ax_in=axes[1],
                                        vmin=vmin, vmax=vmax)
            axis.set_title('Latest 5 games')
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata['plot_pos_radiant'].append(relpath)
            fig.clf()
    # fig.clf()
    return metadata


def do_pregame_routes(team: TeamInfo, r_query, metadata: dict,
                      update_dire: bool, update_radiant: bool, limit=5,
                      cache=True):
    d_replays, r_replays = get_side_replays(r_query, session, team)
    d_replays = d_replays.order_by(Replay.replayID.desc())
    r_replays = r_replays.order_by(Replay.replayID.desc())

    plot_base = Path(PLOT_BASE_PATH)
    team_path: Path = plot_base / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(7, 7))
    cache_dire = Path(environment["CACHE"])

    def _process_side(replays, side: Team):
        s_string = "dire" if side == Team.DIRE else "radiant"
        saved_paths = []
        r: Replay
        i = 0
        for r in replays:
            if not is_full_replay(session, r):
                continue
            if i >= limit:
                break
            r_file = f"{r.replayID}_route_{s_string}.png"
            cache_path = cache_dire / r_file
            destination = team_path / s_string / f"pregame_route_{i}.png"

            if cache and cache_path.exists():
                shutil.copyfile(cache_path, destination)
                saved_paths.append(str(destination.relative_to(plot_base)))
            else:
                plot_pregame_players(r, team, side, session, team_session, fig)
                fig.tight_layout()
                fig.savefig(cache_path)
                shutil.copyfile(cache_path, destination)
                saved_paths.append(str(destination.relative_to(plot_base)))
                fig.clf()
            i += 1
        return saved_paths

    if update_dire:
        metadata[f'pregame_routes_dire'] = _process_side(d_replays, Team.DIRE)
    if update_radiant:
        metadata[f'pregame_routes_radiant'] = _process_side(r_replays, Team.RADIANT)

    return metadata

def do_comparison_report(session, replay_ids: List[int], teams: List[TeamInfo],
                         custom_times=None, identifier=None):
    times = [(0,5), (5, 10), (10, 15), (15, 20)]
    if custom_times is not None:
        times = custom_times

    report_path: Path = Path(PLOT_BASE_PATH) / "REPORTS"
    report_path.mkdir(parents=True, exist_ok=True)
    if identifier is not None:
        report_output = report_path / (f'{teams[0].name}_{teams[1].name}_{identifier}_comparison.pdf')
    else:
        report_output = report_path / (f'{teams[0].name}_{teams[1].name}_comparison.pdf')
    pdf = FPDF()
    # Get individual ones
    p: TeamPlayer
    for slot, (p1, p2) in enumerate(zip(teams[0].players, teams[1].players)):
        team_path: Path = Path(PLOT_BASE_PATH) / "CUSTOM"
        team_path.mkdir(parents=True, exist_ok=True)

        p1_name = p1.name
        steam_id1 = p1.player_id

        p2_name = p2.name
        steam_id2 = p2.player_id
        if identifier is not None:
            post_fix = f'{identifier}_comparison.png'
        else:
            post_fix = f'comparison.png'
        for ti in times:
            fig, axes = plt.subplots(1, 2, figsize=(8.27, 5.845))
            # fig.set_dpi(200)
            plot_positioning(session, replay_ids[0], teams[0], steam_id1,
                             start=ti[0]*60, end=ti[1]*60, axis=axes[0], fig=fig)
            axes[0].set_title(f'{ti[0]} to {ti[1]} mins')
            axes[0].axis('on')
            axes[0].set_xticks([])
            axes[0].set_yticks([])
            axes[0].set_ylabel(p1_name)

            plot_positioning(session, replay_ids[1], teams[1], steam_id2,
                             start=ti[0]*60, end=ti[1]*60, axis=axes[1], fig=fig)
            axes[1].set_title(f'{ti[0]} to {ti[1]} mins')
            axes[1].axis('on')
            axes[1].set_xticks([])
            axes[1].set_yticks([])
            axes[1].set_ylabel(p2_name)

            output = team_path / (f'{p1_name}_{p2_name}_{ti[0]}to{ti[1]}_{post_fix}')
            fig.savefig(output, bbox_inches='tight')
            fig.clf()

            pdf.add_page()
            pdf.image(output, keep_aspect_ratio=True, w=180, h=290)

    pdf.output(report_output)

    
def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team


if __name__ == '__main__':
    team_og = get_team(2586976)
    team_liquid = get_team(2163)
    teams = [team_liquid, team_liquid, team_og]
    replay_ids = [7256512720, 7256414790, 7254795299]

    for te, i in zip(teams, replay_ids):
        # player_heatmap_report(session, i, te)
        # player_route_report(session, i, te)
        pass

    do_comparison_report(session, [7254795299, 7256414790], [team_og, team_liquid])

    # start = 10*60
    # end = 20*60
    # for te, i in zip(teams, replay_ids):
    #     for p in range(5):
    #         plot_positioning(session, i, te, p, start, end, "10to20")
    #         plot_route(session, i, te, team_session, p, start, end, "10to20")