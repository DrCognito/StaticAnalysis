import argparse
import json
import shutil
import time as t
from argparse import ArgumentParser
from datetime import datetime, timedelta
from itertools import zip_longest
from os import mkdir
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pytz
from fpdf import FPDF, Align
from herotools.important_times import ImportantTimes, nice_time_names
from herotools.HeroTools import FullNameMap
from matplotlib import rcParams, ticker
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas import DataFrame, IntervalIndex, cut, read_sql, concat
from propubs.libs.vis import plot_team_pubs, plot_team_pubs_timesplit, get_team_df
from propubs.model.pub_heroes import InitDB as InitPubDB
from propubs.model.team_info import (BAD_TEAM_TIME_SENTINEL,
                                     get_team_last_result)
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from StaticAnalysis.analysis.draft_vis import replay_draft_image
from StaticAnalysis.analysis.Player import player_heroes, player_position, player_position_replays, player_position_replay_id, Player, get_player_dataframe, _heroes_post_process, get_team_dataframes, get_team_dataframes_rquery, _update_post_process, get_hero_winrate, get_hero_picks
from StaticAnalysis.analysis.priority_picks import (priority_picks,
                                                    priority_picks_double)
from StaticAnalysis.analysis.Replay import (counter_picks, draft_summary,
                                            get_ptbase_tslice,
                                            get_ptbase_tslice_side,
                                            get_rune_control, get_side_replays,
                                            get_smoke, hero_win_rate,
                                            pair_rate, win_rate_table)
from StaticAnalysis.analysis.route_vis import plot_pregame_players
from StaticAnalysis.analysis.Stacks import do_stacks
# from StaticAnalysis.analysis.table_picks import create_tables
from StaticAnalysis.analysis.table_picks_panda import create_tables
from StaticAnalysis.analysis.visualisation import (
    dataframe_xy, dataframe_xy_time, dataframe_xy_time_smoke,
    get_binning_percentile_xy, plot_draft_summary, plot_flex_picks,
    plot_hero_winrates, plot_object_position, plot_object_position_scatter,
    plot_pick_context, plot_pick_pairs, plot_player_heroes, plot_runes)
from StaticAnalysis.analysis.ward_vis import (build_ward_table,
                                              plot_drafts_above,
                                              plot_eye_scatter)
from StaticAnalysis.analysis.smoke_vis import get_smoked_player_table, get_smoke_table_replays
from StaticAnalysis.lib.Common import (ChainedAssignment, location_filter,
                                       prepare_retrieve_figure, add_map, EXTENT)
from StaticAnalysis.lib.metadata import (has_picks, is_full_replay, is_updated,
                                         make_meta, has_wards)
from StaticAnalysis.lib.team_info import InitTeamDB, TeamInfo, TeamPlayer
from StaticAnalysis.replays.Player import PlayerStatus
from StaticAnalysis.replays.Replay import InitDB, Replay, Team
from StaticAnalysis.replays.Scan import Scan
from StaticAnalysis.replays.Smoke import Smoke
from StaticAnalysis.replays.TeamSelections import TeamSelections
from StaticAnalysis.replays.Ward import Ward, WardType
from StaticAnalysis.replays.Tormentor import TormentorSpawn, TormentorKill
from StaticAnalysis.vis.tormentor import plot_tormentor_kill_players
import StaticAnalysis
from StaticAnalysis import session, team_session, pub_session, LOG
from StaticAnalysis.analysis.rune import plot_player_routes, plot_player_positions, wisdom_rune_times, wisdom_rune_table, build_wisdom_rune_summary, plot_wisdom_table
from math import isnan
from typing import List
from propubs.libs.vis import process_dataframe_timeplit
from StaticAnalysis.vis.flex_vis import plot_flexstack, combine_pub_comp, get_flex_totals, get_flex_totals_pub, plot_flexstack_pub, fix_pubs_df_index
from propubs.libs import TIME_LABELS
from propubs.libs.vis_comp import process_team_portraits
from sqlalchemy.orm import Query
from tqdm import tqdm, trange
from tqdm.contrib.logging import logging_redirect_tqdm
import concurrent.futures

import warnings
warnings.filterwarnings(
    "error",
    category=FutureWarning
)


PLOT_BASE_PATH = StaticAnalysis.CONFIG['output']['PLOT_OUTPUT']
# Figure dpi output
rcParams['savefig.dpi'] = 100

#region argparse
arguments = ArgumentParser()
arguments.add_argument('--process_teams',
                       help='''Process specific team.''',
                       nargs='+')
arguments.add_argument('--using_leagues',
                       help='''Use replays only from these league ids.''',
                       nargs='*')
arguments.add_argument('--extra_stackid',
                       help='''Extra stack id matching,
                               only one team allowed.''',
                       type=str)
# arguments.add_argument('--use_dataset',
#                        help='''Use this or create a new dataset
#                                for these options.''')
arguments.add_argument('--reprocess',
                       help='''Remake plots regardless of metadata''',
                       action='store_true')
arguments.add_argument('--use_time',
                       help='''Specify a time from herotools.important_times
                               to use for cut.''',
                       nargs='+')
arguments.add_argument('--end_time',
                       help='''Specify a time from herotools.important_times
                               to use for the end of the section.''',
                       nargs='+')
arguments.add_argument('--custom_time',
                       help='''Specity a unix time to over-ride time cut.''',
                       type=int)
arguments.add_argument('--process_all',
                       help='''Process all teams in the TeamInfo database.''',
                       action='store_true')
arguments.add_argument('--skip_datasummary',
                       help='''Skip processing the data set summary plots.''',
                       action='store_true')
arguments.add_argument("--draft", action=argparse.BooleanOptionalAction)
arguments.add_argument("--positioning", action=argparse.BooleanOptionalAction)
arguments.add_argument("--wards", action=argparse.BooleanOptionalAction)
arguments.add_argument("--wards_separate", action=argparse.BooleanOptionalAction)
arguments.add_argument("--pregame_positioning", action=argparse.BooleanOptionalAction)
arguments.add_argument("--smoke", action=argparse.BooleanOptionalAction)
arguments.add_argument("--scans", action=argparse.BooleanOptionalAction)
arguments.add_argument("--summary", action=argparse.BooleanOptionalAction)
arguments.add_argument("--prioritypicks", action=argparse.BooleanOptionalAction)
arguments.add_argument("--counters", action=argparse.BooleanOptionalAction)
arguments.add_argument("--runes", action=argparse.BooleanOptionalAction)
arguments.add_argument("--tormentors", action=argparse.BooleanOptionalAction)

arguments.add_argument('--default_off', action='store_true', default=False)
arguments.add_argument('--pubs_updated', action='store_true', default=False)
arguments.add_argument('--scrim_time',
                       help='''Time cut for the scrims to be processed at.''')
arguments.add_argument('--scrim_endtime',
                       help='''Time cut for the scrims to be ended at.''')
arguments.add_argument('--statistic_time',
                       help='''Time cut for the statistical win rates.''')
#endregion


def get_create_metadata(team: TeamInfo, dataset="default"):
    team_path = Path(PLOT_BASE_PATH) / team.name
    dataset_path: Path = team_path / dataset
    if not team_path.exists():
        LOG.debug("Adding new team {}.".format(team.name))
        # Will make the whole tree up to path
        team_path.mkdir(parents=True, exist_ok=True)
        mkdir(team_path / 'wards')

    if not dataset_path.exists():
        dataset_path.mkdir(parents=True, exist_ok=True)
        mkdir(dataset_path / 'dire')
        mkdir(dataset_path / 'radiant')
        mkdir(dataset_path / 'counters')

    meta_json = team_path / 'meta_data.json'
    if meta_json.exists():
        with open(meta_json, 'r') as file:
            json_file = json.load(file)
        if dataset in json_file:
            return json_file[dataset]
        if dataset is None:
            return json_file

    return make_meta(dataset)


def store_metadata(team: TeamInfo, metadata):
    team_path = Path(PLOT_BASE_PATH) / team.name
    meta_json = team_path / 'meta_data.json'

    if meta_json.exists():
        with open(meta_json, 'r') as file:
            json_file = json.load(file)
    else:
        json_file = {}

    json_file[metadata['name']] = metadata
    with open(meta_json, 'w') as file:
        json.dump(json_file, file)

    return meta_json


def store_generalstats(team: TeamInfo, statstring: str):
    team_path = Path(PLOT_BASE_PATH) / team.name
    meta_json = team_path / 'meta_data.json'

    if meta_json.exists():
        with open(meta_json, 'r') as file:
            json_file = json.load(file)
    else:
        team_path.mkdir(parents=True, exist_ok=True)
        json_file = {}

    json_file['general_stats'] = statstring
    with open(meta_json, 'w') as file:
        json.dump(json_file, file)

    return meta_json


def get_generalstats(team: TeamInfo):
    team_path = Path(PLOT_BASE_PATH) / team.name
    meta_json = team_path / 'meta_data.json'

    if meta_json.exists():
        with open(meta_json, 'r') as file:
            json_file = json.load(file)

    return json_file.get('general_stats')


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

    for pos in (posbar := tqdm(positions, position=3, leave=False)):
        if pos >= len(team.players):
            LOG.error("Position {} is out of range for {}"
                  .format(pos, team.name))
        p_name = team.players[pos].name
        posbar.set_description(p_name)
        metadata['player_names'].append(p_name)
        (pos_dire, pos_dire_limited),\
            (pos_radiant, pos_radiant_limited) = player_position(session, r_query, team,
                                                                 player_slot=pos,
                                                                 start=start, end=end,
                                                                 recent_limit=recent_limit)
        if update_dire:
            fig, axes = plt.subplots(1, 2, figsize=(15, 10))

            output = team_path / 'dire' / (p_name + '.jpg')

            pos_dire_df = dataframe_xy(pos_dire, PlayerStatus, session)
            if pos_dire_df.empty:
                LOG.warning("No data for {} on Dire.".format(team.players[pos].name))
            vmin, vmax = get_binning_percentile_xy(pos_dire_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_dire_df,
                                        bins=64, fig_in=fig, ax_in=axes[0],
                                        vmin=vmin, vmax=vmax)

            pos_dire_limited_df = dataframe_xy(pos_dire_limited, PlayerStatus, session)
            if pos_dire_limited_df.empty and not pos_dire_df.empty:
                LOG.warning(f"No data for {team.players[pos].name} on Dire for limited ({recent_limit}).")
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
            fig, axes = plt.subplots(1, 2, figsize=(15, 10))

            output = team_path / 'radiant' / (p_name + '.jpg')

            pos_radiant_df = dataframe_xy(pos_radiant, PlayerStatus, session)
            if pos_radiant_df.empty:
                LOG.warning("No data for {} on Radiant.".format(team.players[pos].name))
            vmin, vmax = get_binning_percentile_xy(pos_radiant_df)
            vmin = max(1.0, vmin)
            axis = plot_object_position(pos_radiant_df,
                                        bins=64, fig_in=fig, ax_in=axes[0],
                                        vmin=vmin, vmax=vmax)

            # pos_radiant_limited = pos_radiant_limited.filter(ancient_filter)
            pos_radiant_limited_df = dataframe_xy(pos_radiant_limited, PlayerStatus, session)
            if pos_radiant_limited_df.empty and not pos_radiant_df.empty:
                LOG.warning(f"No data for {team.players[pos].name} on Radiant for limited ({recent_limit}).")
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


def do_draft(team: TeamInfo, metadata,
             update_dire=True, update_radiant=True,
             r_filter=None, per_side_limit=None, scrim_list: list = None):
    '''Produces draft images from the replays in r_query.
       Will only proceed for sides with update = True.
    '''
    if not update_dire and not update_radiant:
        return metadata

    if r_filter is None:
        r_filter = team.filter
    else:
        r_filter = and_(r_filter, team.filter)
    r_drafted = session.query(Replay).filter(r_filter)\
                                     .outerjoin(TeamSelections)\
                                     .filter(TeamSelections.draft.any())\
                                     .order_by(Replay.replayID.desc())

    dire_filter = Replay.get_side_filter(team, Team.DIRE)
    radiant_filter = Replay.get_side_filter(team, Team.RADIANT)
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)

    def _save_store(drafts: list, file_stem: str):
        outputs = []
        for count, d in enumerate(drafts):
            output = team_path / f"{file_stem}_{count}.png"

            # d = d.convert("RGB")
            d.save(output, dpi=(50, 50), optimize=True)

            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            outputs.append(relpath)

        return outputs

    def _clean_up_plots(paths: list):
        """Assumes the path is saved as a relative path"""
        if not paths:
            return
        if type(paths) is not list:
            paths = [paths, ]
        for p in paths:
            plot_path: Path = Path(PLOT_BASE_PATH) / p
            try:
                plot_path.unlink()
            except FileNotFoundError:
                LOG.warning(f"Plot not found! {plot_path}")

    if update_dire:
        if per_side_limit is not None:
            replays = r_drafted.filter(dire_filter).order_by(Replay.replayID.desc())\
                               .limit(2*per_side_limit).all()
        else:
            replays = r_drafted.filter(dire_filter).order_by(Replay.replayID.desc())\
                               .all()
        dire_drafts = replay_draft_image(replays,
                                         team,
                                         team.name,
                                         scrim_list=scrim_list)
        _clean_up_plots(metadata.get('plot_dire_drafts'))
        if dire_drafts is not None:
            metadata['plot_dire_drafts'] = _save_store(dire_drafts, 'dire/drafts')

    if update_radiant:
        if per_side_limit is not None:
            replays = r_drafted.filter(radiant_filter).order_by(Replay.replayID.desc())\
                               .limit(2*per_side_limit).all()
        else:
            replays = r_drafted.filter(radiant_filter).order_by(Replay.replayID.desc())\
                               .all()
        radiant_drafts = replay_draft_image(replays,
                                            team,
                                            team.name,
                                            scrim_list=scrim_list)
        _clean_up_plots(metadata.get('plot_radiant_drafts'))
        if radiant_drafts is not None:
            metadata['plot_radiant_drafts'] = _save_store(radiant_drafts, 'radiant/drafts')

    if update_radiant or update_dire:
        if per_side_limit is not None:
            replays = r_drafted.order_by(Replay.replayID.desc())\
                               .limit(2*per_side_limit).all()
        else:
            replays = r_drafted.order_by(Replay.replayID.desc())\
                               .all()

        drafts_first = replay_draft_image(replays,
                                          team,
                                          team.name,
                                          second_pick=False,
                                          scrim_list=scrim_list)
        _clean_up_plots(metadata.get('plot_drafts_first'))
        if drafts_first is not None:
            metadata['plot_drafts_first'] = _save_store(drafts_first, 'drafts_first')

        drafts_second = replay_draft_image(replays,
                                           team,
                                           team.name,
                                           first_pick=False,
                                           scrim_list=scrim_list)
        _clean_up_plots(metadata.get('plot_drafts_second'))
        if drafts_second is not None:
            metadata['plot_drafts_second'] = _save_store(drafts_second, 'drafts_second')

        drafts_all = replay_draft_image(replays,
                                        team,
                                        team.name,
                                        scrim_list=scrim_list)
        _clean_up_plots(metadata.get('plot_drafts_all'))
        if drafts_all is not None:
            metadata['plot_drafts_all'] = _save_store(drafts_all, 'drafts_all')

    return metadata


def do_wards_separate(team: TeamInfo, r_query,
                      metadata: dict,
                      update_dire=True, update_radiant=True,
                      time_range=(-2*60, 20*60),
                      limit=None):
    """Plots per replay ward plots and returns assosciated metadata for a query.

    Arguments:
        team {TeamInfo} -- TeamInfo object corresponding to processing team.
        r_query {[type]} -- Fitlered query for replays containing team.
        metadata {dict} -- Metadata dictionary to be accessed and returned.

    Keyword Arguments:
        update_dire {bool} -- Process dire replays for team. (default: {True})
        update_radiant {bool} -- Process radiant replays for team. (default: {True})
    """
    if not update_dire and not update_radiant:
        return metadata
    team_path: Path = Path(PLOT_BASE_PATH) / team.name
    dire_loc: Path = team_path / "wards"
    radiant_loc: Path = team_path / "wards"
    (team_path / 'wards').mkdir(parents=True, exist_ok=True)

    # fig, ax = plt.subplots(figsize=(10, 13))
    fig = plt.figure(figsize=(10, 13))
    fig.set_tight_layout(True)
    # Get width only once as subsequent widths are weird!
    fixed_width = None

    def _get_ax_size(ax_in, fig_in):
        bbox = ax_in.get_window_extent()\
                    .transformed(fig_in.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= fig_in.dpi
        height *= fig_in.dpi
        return width, height

    def _process_ward_replay(side: Team, r_query, replay_id,
                             time_range=(-2*60, 20*60)):
        nonlocal fixed_width
        nonlocal fig
        # fig.clf('reset')
        # fig = plt.gcf()
        # ax = plt.gca()
        ax = fig.subplots()
        if side == Team.DIRE:
            outloc = dire_loc / (str(replay_id) + ".png")
            r_name = "Opposition"
            d_name = team.name
        else:
            outloc = radiant_loc / (str(replay_id) + ".png")
            d_name = "Opposition"
            r_name = team.name

        if outloc.exists():
            return str(outloc.relative_to(Path(PLOT_BASE_PATH)))

        r_query = r_query.filter(Replay.replayID == replay_id)
        try:
            wards = get_ptbase_tslice_side(session, r_query, team=team,
                                           Type=Ward,
                                           side=side,
                                           start=-2*60, end=20*60)
        except LookupError as e:
            LOG.error(f"Failed to process slice! wards for. Error:\n{e}")
        wards = wards.filter(Ward.ward_type == WardType.OBSERVER)

        data = build_ward_table(wards, session, team_session, team)
        if data.empty:
            LOG.debug(f"Ward table empty! {replay_id}: {side}")
            return None
        # fig, ax = plt.subplots(figsize=(10, 13))
        if fixed_width is None:
            fixed_width, _ = _get_ax_size(ax, fig)
        extras = plot_eye_scatter(data, ax, size=(18, 14))
        drafts = plot_drafts_above(r_query, ax, fixed_width,
                                   r_name=r_name,
                                   d_name=d_name)
        ax.text(s=str(replay_id), x=0, y=0,
                ha='left', va='bottom', zorder=5,
                path_effects=[PathEffects.withStroke(linewidth=3,
                              foreground="w")],
                color='black',
                transform=ax.transAxes)
        # fig.set_tight_layout(True)
        fig.tight_layout(pad=2.0)
        # fig.savefig(outloc, bbox_extra_artists=(*drafts, *extras))
        fig.savefig(outloc)
        # for a in fig.axes:
        #     a.cla()
        fig.clf()
        return str(outloc.relative_to(Path(PLOT_BASE_PATH)))

    def _process_side(side: Team, replays):
        if limit is not None:
            r_ids = replays.with_entities(Replay.replayID).limit(limit)
        else:
            r_ids = replays.with_entities(Replay.replayID)
        if side == Team.DIRE:
            out_key = "wards_dire"
        else:
            out_key = "wards_radiant"
        metadata[out_key] = {}
        r: Replay
        for r, in r_ids:
            # try:
            new_plot = _process_ward_replay(side, r_query, r,
                                            time_range)
            fig.clf()
            if new_plot is not None:
                metadata[out_key][r] = new_plot

    d_replays, r_replays = get_side_replays(r_query, session, team)
    d_replays = d_replays.order_by(Replay.replayID.desc())
    r_replays = r_replays.order_by(Replay.replayID.desc())
    if update_dire:
        _process_side(Team.DIRE, d_replays)
    if update_radiant:
        _process_side(Team.RADIANT, r_replays)

    return metadata


def do_wards(team: TeamInfo, r_query,
             metadata: dict,
             update_dire=True, update_radiant=True,
             replay_limit=None):

    if not update_dire and not update_radiant:
        return metadata
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)
    vmin, vmax = (1, 5)

    wards_dire, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                                  Type=Ward,
                                                  start=-2*60,
                                                  end=12*60,
                                                  replay_limit=replay_limit)
    wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
    wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)
    metadata['plot_ward_names'] = ["Pregame", "0 to 7 mins", "7 to 15 mins",
                                   ">15 mins"]
    fig, _ = plt.subplots(figsize=(10, 10))
    fig.clf()

    def _plot_wards(data: DataFrame, p_out: Path):
        plot_object_position(data, fig_in=fig, vmin=vmin, vmax=vmax)
        fig.tight_layout()
        fig.savefig(p_out)
        fig.clf()
        return

    if update_dire:
        metadata['plot_ward_dire'] = []
        output = team_path / 'dire'
        ward_df = dataframe_xy_time(wards_dire, Ward, session)

        p_out = output / 'wards_pregame.jpg'
        _plot_wards(ward_df.loc[ward_df['game_time'] <= 0], p_out)
        relpath = p_out.relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

        p_out = output / 'wards_0to7.jpg'
        _plot_wards(ward_df.loc[(ward_df['game_time'] > 0) &
                                (ward_df['game_time'] <= 7*60)],
                    p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

        p_out = output / 'wards_7to15.jpg'
        _plot_wards(ward_df.loc[(ward_df['game_time'] > 7*60) &
                                (ward_df['game_time'] <= 15*60)],
                    p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

        p_out = output / 'wards_gt15.jpg'
        _plot_wards(ward_df.loc[(ward_df['game_time'] > 15)],
                    p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

    if update_radiant:
        metadata['plot_ward_radiant'] = []
        output = team_path / 'radiant'
        ward_df = dataframe_xy_time(wards_radiant, Ward, session)

        p_out = output / 'wards_pregame.jpg'
        _plot_wards(ward_df.loc[ward_df['game_time'] <= 0], p_out)
        relpath = p_out.relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_radiant'].append(str(relpath))

        p_out = output / 'wards_0to7.jpg'
        _plot_wards(ward_df.loc[(ward_df['game_time'] > 0) &
                                (ward_df['game_time'] <= 7*60)],
                    p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_radiant'].append(str(relpath))

        p_out = output / 'wards_7to15.jpg'
        _plot_wards(ward_df.loc[(ward_df['game_time'] > 7*60) &
                                (ward_df['game_time'] <= 15*60)],
                    p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_radiant'].append(str(relpath))

        p_out = output / 'wards_gt15.jpg'
        _plot_wards(ward_df.loc[(ward_df['game_time'] > 15)],
                    p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_radiant'].append(str(relpath))

    return metadata


def do_smoke(team: TeamInfo, r_query, metadata: dict,
             update_dire=True, update_radiant=True):
    '''Makes plots for smoke starting points in r_query.
       Separate plots are made for a number of times.
       update_dire and update_radiant control updating specific side.
    '''
    if not update_dire and not update_radiant:
        return metadata

    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)
    time_pairs = [
        (-10*60, 0*60),
        (8*60, 15*60),
    ]

    vmin, vmax = (1, 5)

    time_titles = [
        'Pre-Game',
        '8 mins to 15 mins',
    ]
    s_dire, s_radiant = get_smoke(r_query, session, team)

    def _plot_time_slice(times, title, data, axis):
        data_slice = data.loc[(data['game_start_time'] > times[0]) &
                              (data['game_start_time'] <= times[1])]
        if data_slice['xCoordinate'].isnull().all():
            return
        axis = plot_object_position(data_slice, bins=16, ax_in=axis,
                                    vmin=vmin, vmax=vmax)
        axis.set_title(title)
    
    def _plot_time_slice(times, title, data, axis):
        data = get_smoke_table_replays(
                r_query, team, side, session, team_session,
                times[0], times[1]
                )
        axis = plot_object_position(data_slice, bins=16, ax_in=axis,
                                    vmin=vmin, vmax=vmax)
        axis.set_title(title)

    def _process_side(query, side: Team):
        fig, axList = plt.subplots(1, 2, figsize=(12, 6))

        for tpair, title, axe in zip(time_pairs, time_titles, axList):
            df = get_smoke_table_replays(
                r_query, team, side, session, team_session,
                tpair[0], tpair[1]
                )
            if df.empty:
                axe.text(0.5, 0.5, "No Data", fontsize=18,
                      horizontalalignment='center',
                      verticalalignment='center')
                axe.set_title(title)
                axe.yaxis.set_ticks([])
                axe.xaxis.set_ticks([])
            else:
                df['xCoordinate'] = df.loc[:, 'averageXCoordinateStart']
                df['yCoordinate'] = df.loc[:, 'averageYCoordinateStart']
                axe = plot_object_position(
                    df,
                    bins=16, ax_in=axe,
                    vmin=vmin, vmax=vmax
                    )
                axe.set_title(title)

        team_str = 'dire' if side == Team.DIRE else 'radiant'
        output = team_path / '{}/smoke_summary.jpg'.format(team_str)
        fig.tight_layout()
        fig.subplots_adjust(wspace=0.05)
        fig.savefig(output)
        plt.close(fig)
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_smoke_{}'.format(team_str)] = relpath
        
        # Smoke tables
        metadata[f'table_smoke_{team_str}'] = {}
        for tpair, title in zip(time_pairs, time_titles):
            df = get_smoked_player_table(
                r_query, team, side, session, team_session,
                tpair[0], tpair[1]
                )
            if df.empty:
                metadata[f'table_smoke_{team_str}'][title] = None
            else:
                metadata[f'table_smoke_{team_str}'][title] = df.to_html()

    if update_dire:
        _process_side(s_dire, Team.DIRE)
    if update_radiant:
        _process_side(s_radiant, Team.RADIANT)

    return metadata


def do_scans(team: TeamInfo, r_query, metadata: dict,
             update_dire=True, update_radiant=True):
    '''Makes plots for the scan origin points for replays in r_query.
       update_dire and update_radiant control updating specific sides.
    '''
    if not update_dire and not update_radiant:
        return metadata

    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)

    s_dire, s_radiant = get_ptbase_tslice(session, r_query,
                                          team=team, Type=Scan)

    fig, _ = plt.subplots(figsize=(10, 13))
    fig.clf()

    def _plot_scans(query, side: Team):
        data = dataframe_xy_time(query, Scan, session)
        plot_object_position_scatter(data, fig_in=fig)

        team_str = 'dire' if side == Team.DIRE else 'radiant'
        output = team_path / '{}/scan_summary.jpg'.format(team_str)
        fig.savefig(output, bbox_inches='tight')
        fig.clf()
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_scan_{}'.format(team_str)] = relpath

    if update_dire:
        _plot_scans(s_dire, Team.DIRE)
    if update_radiant:
        _plot_scans(s_radiant, Team.RADIANT)

    return metadata


def do_priority_picks(team, r_query, metadata):
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    output = team_path / "pick_priority.png"

    fig = plt.figure()
    fig = priority_picks_double(team, r_query, fig, nHeroes=10)
    fig.tight_layout(w_pad=1.22, h_pad=2.5)
    fig.savefig(output, bbox_inches="tight")
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['pick_priority'] = relpath
    fig.clf()

    return metadata


def do_portrait_picks(
    team: TeamInfo, metadata: dict, r_query: Query, use_team=False,
    min_time: datetime = None
    ) -> dict:
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    
    table_cols = [Player.hero, Player.win, Player.endGameTime]
    if use_team:
        comp_df = get_team_dataframes_rquery(
            team, r_query,
            table_cols, session, _heroes_post_process
        )
    else:
        comp_df = get_team_dataframes(
            team, table_cols, min_time,
            session, _heroes_post_process
        )

    def add_extra_cols(
        player: TeamPlayer | int, df: DataFrame, session: Session = session,
        r_query: Query = None) -> DataFrame:
        if df.empty:
            return df

        df['0to7 winrate'] = df.index.map(
            lambda x : get_hero_winrate(
                player, x, session,
                ImportantTimes['PreviousWeek'], ImportantTimes['Now'],
                r_query
                )
        )
        df['0to7 picks'] = df.index.map(
        lambda x : get_hero_picks(
            player, x, session, ImportantTimes['PreviousWeek'], ImportantTimes['Now'], r_query
            )
        )
        
        df['0to14 winrate'] = df.index.map(
            lambda x : get_hero_winrate(
                player, x, session,
                ImportantTimes['PreviousFortnight'], ImportantTimes['Now'],
                r_query
                )
        )
        
        return df
    # Add the winrate columns by player
    for p in team.players:
        df = comp_df.get(p.name)
        if df is not None:
            add_extra_cols(p, df, r_query=r_query)

    # Uses MAIN_TIME to get the missing comp heroes
    update_df = get_team_dataframes(
        team,
        table_cols, post_process = _update_post_process)
    full_table = process_team_portraits(
        team,
        comp_df,
        update_df
    )
    output = team_path / f'hero_picks_portrait.png'
    full_table.save(output)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['hero_picks_portrait'] = relpath
    
    return metadata


def do_player_picks(team: TeamInfo, metadata: dict,
                    r_filter, limit=None, postfix='',
                    mintime=None, maxtime=None):
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)

    fig = plt.figure()
    fig.set_size_inches(8.27, 11.69)

    hero_picks_df = player_heroes(session, team, r_filt=r_filter, limit=limit, summarise=False)
    axes_first = fig.subplots(5)

    extra = plot_player_heroes(hero_picks_df, axes_first)
    axes_first[0].set_title("Matches")
    # fig.tight_layout(h_pad=2.0)
    output = team_path / f'hero_picks{postfix}.png'
    # fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=200)
    # fig.tight_layout(w_pad=1.22, h_pad=2.5)
    fig.subplots_adjust(wspace=0.04, left=0.06, right=0.94, top=0.97, bottom=0.04)
    # fig.tight_layout()
    # fig.savefig(output, bbox_inches="tight", bbox_extra_artists=extra)
    # fig.savefig(output, bbox_extra_artists=extra)
    fig.savefig(output)
    fig.clf()
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata[f'plot_hero_picks{postfix}'] = relpath

    return metadata

def do_flex_pubs(team: TeamInfo, metadata: dict, min_time: datetime, end_time: datetime = None):
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)

    flex_pubs_df = get_team_df(team, pub_session, min_time,
        post_process=process_dataframe_timeplit, maxtime=end_time)
    # Fix me chain with post_process?
    flex_pubs_df = fix_pubs_df_index(flex_pubs_df)
    
    output = team_path / f'hero_flex_pubs.png'
    fig = plt.figure()
    fig = plot_flexstack_pub(flex_pubs_df, contexts=TIME_LABELS, fig=fig)
    fig.savefig(output, bbox_inches='tight', dpi=150)
    fig.clf()
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata[f'plot_flex_pubs'] = relpath

    return metadata


def do_summary(team: TeamInfo, r_query, metadata: dict, r_filter, limit=None, postfix=''):
    '''Plots draft summary, player picks, pick pairs and hero win rates
       for the replays in r_query.'''
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)

    fig = plt.figure()
    draft_summary_df = draft_summary(session, r_query, team, limit=limit)
    fig, extra = plot_draft_summary(*draft_summary_df, fig)
    output = team_path / f'draft_summary{postfix}.png'
    # fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
    fig.subplots_adjust(wspace=0.1, hspace=0.25)
    fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight')
    fig.clf()
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata[f'plot_draft_summary{postfix}'] = relpath

    def _is_flex(*args):
        pass_count = 0
        for p in args:
            if p >= 1:
                pass_count += 1
        return pass_count
    flex_picks = player_heroes(session, team, r_filt=r_filter, limit=limit, nHeroes=200)
    flex_picks['Counts'] = flex_picks.apply(lambda x: _is_flex(*x), axis=1)
    flex_picks = flex_picks.query('Counts > 1')
    with ChainedAssignment():
        flex_picks['std'] = flex_picks.iloc[:, 0:-1].std(axis=1)
        flex_picks['Name'] = flex_picks.index.map(FullNameMap)
    # flex_picks = flex_picks.sort_values(['Counts', 'std'], ascending=True)
    flex_picks = flex_picks.sort_values(['Name'], ascending=False)
    fig, extra = plot_flex_picks(flex_picks.iloc[:, 0:-3], fig)
    output = team_path / f'hero_flex{postfix}.png'
    fig.savefig(output, bbox_extra_artists=extra,
                bbox_inches='tight', dpi=150)
    fig.clf()
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata[f'plot_hero_flex{postfix}'] = relpath

    pick_pair_df = pair_rate(session, r_query, team, limit=limit)
    if pick_pair_df:
        fig, extra = plot_pick_pairs(pick_pair_df, fig)
        output = team_path / f'pick_pairs{postfix}.png'
        fig.tight_layout(h_pad=1.5)
        fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
        fig.clf()
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_pair_picks{postfix}'] = relpath

    if not draft_summary_df[0].empty:
        fig, _, extra = plot_pick_context(draft_summary_df[0], team, r_query, fig, limit=limit)
        output = team_path / f'pick_context{postfix}.png'
        # fig.tight_layout(h_pad=3.0)
        fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=800)
        fig.clf()
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_pick_context{postfix}'] = relpath

    hero_win_rate_df = hero_win_rate(r_query, team, limit=limit)
    fig, _ = plot_hero_winrates(hero_win_rate_df, fig)
    output = team_path / f'hero_win_rate{postfix}.png'
    # fig.tight_layout(h_pad=3.0)
    fig.savefig(output, bbox_inches='tight', dpi=300)
    fig.clf()
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata[f'plot_win_rate{postfix}'] = relpath

    rune_df = get_rune_control(r_query, team, limit=limit)
    # One line
    one_line = len(rune_df) == 1
    # All that line is 0
    zeroed = all((rune_df.iloc[0] == [0, 0, 0, 0, 0, 0, 0, 0]).to_list())
    if not one_line and not zeroed:
        fig, _ = plot_runes(rune_df, team, fig)
        output = team_path / f'rune_control{postfix}.png'
        fig.tight_layout()
        fig.subplots_adjust(hspace=0.35)
        fig.savefig(output, bbox_inches='tight', dpi=200)
        fig.clf()
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_rune_control{postfix}'] = relpath

    # if limit is not None:
    #     output = team_path / "pick_tables.png"
    #     table_image = create_tables(r_query, session, team)
    #     table_image.save(output)
    #     relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    #     metadata['plot_picktables'] = relpath

    if limit is not None:
        output = team_path / "pick_tables.png"
        table_image = create_tables(r_query, team)
        table_image.save(output)
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_picktables'] = relpath

    return metadata


def exector_plot_fig_path(fig, path):
    fig.tight_layout()
    fig.savefig(path)
    fig.clf()
    plt.close(fig)
    LOG.debug(f"Executor finished {path}.")
    return


def do_runes(team: TeamInfo, r_query, metadata: dict, new_dire: bool, new_radiant: bool,
            reprocess: bool = False) -> dict:
    if not new_dire and not new_radiant:
        return metadata
    # Check out directories exist
    team_path = Path(PLOT_BASE_PATH) / team.name

    meta_path = team_path / metadata['name']
    meta_path.mkdir(parents=True, exist_ok=True)

    positions = team_path / 'positions'
    positions.mkdir(parents=True, exist_ok=True)


    # This MUST be cast to into or sqlalchemy can not filter with it and effectively imposes no limit!
    rune_times = wisdom_rune_times(r_query, max_time=13 * 60)
    rune_table = wisdom_rune_table(r_query, max_time=13*60)
    rune_table = build_wisdom_rune_summary(rune_table, team_session)


    r: Replay
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
        for r in r_query:
            # fig = plt.figure(figsize=(8.27, 8.27))
            fig, axis = plt.subplots()
            fig.set_size_inches(8.27, 8.27)
            rune_max = rune_times[rune_times['replayID'] == r.replayID]['game_time'].max()
            if isnan(rune_max):
                LOG.debug(f"No wisdom rune results for {r.replayID}")
                continue
            # Check to see if we should process this replay
            out_path = positions / f"{r.replayID}.png"
            if out_path.exists() and not reprocess:
                continue
            # Get the table of positions
            rune_min = int(rune_times[rune_times["replayID"] == r.replayID]["game_time"].min()) - 30
            rune_max = int(rune_max)
            table = player_position_replay_id(
                session, r.replayID,
                start=rune_min, end=rune_max
                )
            # team_id_map = lambda x: r.get_team_id_player(x['steamID'])
            if table.empty:
                # No position data
                continue
            table['team_id'] = table['steamID'].map(r.get_team_id_player)
            table['team'] = table['steamID'].map(r.player_side_map)
            side = r.get_side(team)
            if side is None:
                LOG.error(f"[Rune] Could not determine side for {team.name} in {r.replayID}")
            # axis = fig.subplots()
            add_map(axis, extent=EXTENT)
            plot_player_routes(table, team, axis)
            
            df = rune_table.loc[rune_table.loc[:,'replayID'] == r.replayID].drop('replayID', axis=1)
            plot_wisdom_table(df, axis)
            LOG.debug(f"Submitting rune plot to executor for {r.replayID} total figures: {len(plt.get_fignums())}")
            executor.submit(exector_plot_fig_path, fig, out_path)
            # fig.tight_layout()
            # fig.savefig(out_path)
            # fig.clf()
        
            if side == Team.DIRE:
                (metadata.get("rune_routes_7m_dire", [])).append(str(out_path.relative_to(Path(PLOT_BASE_PATH))))
            elif side == Team.RADIANT:
                (metadata.get("rune_routes_7m_radiant", [])).append(str(out_path.relative_to(Path(PLOT_BASE_PATH))))
    LOG.debug(f"Remaining figures: {len(plt.get_fignums())}")

    return metadata


def do_counters(team: TeamInfo, r_query, metadata: dict):
    counters_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    counters_path = counters_path / 'counters'
    counters_path.mkdir(parents=True, exist_ok=True)

    # picks are columns, what they picked into are rows
    counters = counter_picks(session, r_query, team)

    # Remove 0 columns (unpicked heroes)
    counters = counters.T[counters.any()].T
    # Reset the metadata or old heroes remain.
    metadata['counter_picks'] = {}
    # Reusable fig
    fig = plt.figure()

    for hero in counters:
        axis = fig.subplots()

        bar_data = counters[hero].loc[lambda x: x != 0]\
                                 .sort_values(ascending=False)
        bar_data.plot.bar(ax=axis)

        axis.yaxis.set_major_locator(MaxNLocator(integer=True))

        output = counters_path / (hero + '.jpg')
        fig.savefig(output,  bbox_inches='tight')
        fig.clf()
        relpath = output.relative_to(Path(PLOT_BASE_PATH))
        metadata['counter_picks'][hero] = str(relpath)

    return metadata


def do_statistics(team: TeamInfo, r_query, table=True):
    win_rate_df = win_rate_table(r_query, team)
    win_rate_df = win_rate_df.fillna(0)
    win_rate_df = win_rate_df.round(2)

    main_str = [
        f"{win_rate_df.loc['Radiant']['All']:.0f} games Radiant ({win_rate_df.loc['Radiant']['All Percent']}% win rate)<br>",
        f"{win_rate_df.loc['Dire']['All']:.0f} games Dire ({win_rate_df.loc['Dire']['All Percent']}% win rate)<br>",
        "<br>",
        f"{win_rate_df.loc['All']['First']:.0f} games 1st Pick ({win_rate_df.loc['All']['First Pick Percent']}% win Rate)<br>",
        f"{win_rate_df.loc['All']['Second']:.0f} games 2nd Pick ({win_rate_df.loc['All']['Second Pick Percent']}% win rate)<br>",
        "<br>"
    ]
    win_rate_df['Matches'] = win_rate_df['All'].astype(float).astype(int)
    # win_rate_df['Matches'] = win_rate_df['Matches'].replace('.0', '')
    if table:
        main_str = [
            win_rate_df[['First Pick Percent', 'Second Pick Percent', 'Matches']].to_html(),
            "<br>",
            *main_str
        ]
    return '\n'.join(main_str)


def do_tormentor_routes(
    team: TeamInfo, r_query, metadata: dict,
    update_dire: bool, update_radiant: bool,
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
    cache_dire = Path(StaticAnalysis.CONFIG['cache']["CACHE"])

    def _process_side(replays, side: Team):
        s_string = "dire" if side == Team.DIRE else "radiant"
        saved_paths = []
        r: Replay
        for r in replays:
            if not is_full_replay(session, r):
                continue
            r_file = f"{r.replayID}_tormentor1_{s_string}.png"
            cache_path = cache_dire / r_file
            destination = team_path / s_string / f"tormentor1_{r.replayID}.png"

            if cache and destination.exists():
                saved_paths.append(str(destination.relative_to(plot_base)))
                continue
            elif cache and cache_path.exists():
                shutil.copyfile(cache_path, destination)
                saved_paths.append(str(destination.relative_to(plot_base)))
            else:
                tormentor_spawns: List[TormentorSpawn] = list(r.tormentor_spawns)
                tormentor_kills: List[TormentorKill] = list(r.tormentor_kills)
                if not tormentor_kills:
                    LOG.debug(f"No tormentor kills registered for {r.replayID}")
                    continue
                if not tormentor_spawns:
                    LOG.debug(f"No tormentor spawns registered for {r.replayID}")
                    continue
                tspawn = tormentor_spawns[0].game_time
                tkill = tormentor_kills[0].game_time
                spawn_location = (
                    tormentor_spawns[0].xCoordinate,
                    tormentor_spawns[0].yCoordinate)
                # Time range info
                min_time = tspawn - 1*60
                time_slice = tkill - min_time
                # Do the plot!
                plot_tormentor_kill_players(
                    r, team, side, session, team_session,
                    tkill, spawn_location, fig, time_slice=time_slice)
                # Save it
                fig.tight_layout()
                fig.savefig(cache_path)
                shutil.copyfile(cache_path, destination)
                saved_paths.append(str(destination.relative_to(plot_base)))
                fig.clf()
        return saved_paths

    if update_dire:
        metadata[f'tormentor_routes_dire'] = _process_side(d_replays, Team.DIRE)
    if update_radiant:
        metadata[f'tormentor_routes_radiant'] = _process_side(r_replays, Team.RADIANT)

    return metadata


def do_pregame_routes(team: TeamInfo, r_query, metadata: dict,
                      update_dire: bool, update_radiant: bool, limit=None,
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
    cache_dire = Path(StaticAnalysis.CONFIG['cache']["CACHE"])

    def _process_side(replays, side: Team):
        s_string = "dire" if side == Team.DIRE else "radiant"
        saved_paths = []
        r: Replay
        i = 0
        for r in replays:
            # if not is_full_replay(session, r):
            #     continue
            if not has_wards(session, r):
                continue
            if limit is not None and i >= limit:
                break
            r_file = f"{r.replayID}_route_{s_string}.png"
            cache_path = cache_dire / r_file
            destination = team_path / s_string / f"pregame_{r.replayID}.png"

            if cache and destination.exists():
                saved_paths.append(str(destination.relative_to(plot_base)))
                continue
            elif cache and cache_path.exists():
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


def do_general_stats(team: TeamInfo, time: datetime, args: argparse.Namespace,
                     replay_list=None):
    extra_stackid = args.extra_stackid
    if extra_stackid is not None:
        team.extra_stackid = extra_stackid
    r_filter = Replay.endTimeUTC >= time

    if replay_list:
        r_filter = or_(and_(Replay.replayID.in_(replay_list), r_filter), r_filter)
    try:
        r_query = team.get_replays(session).filter(r_filter)
    except SQLAlchemyError as e:
        LOG.opt(exception=True).error("Failed to retrieve replays for team {}".format(team.name))
        # LOG.error(e)
        quit()

    return do_statistics(team, r_query, table=False)


def make_report(team: TeamInfo, metadata: dict, output: Path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 24)
    dataset = nice_time_names.get(metadata['name'], metadata['name'])
    time_string = metadata.get('time_string', "(No replay data)")
    pdf.multi_cell(0, 10, f"{team.name} {time_string}, {dataset}", align="c", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', size=12)
    # Stats
    pdf.cell(0, 5, f"Win rates:", new_x="LMARGIN", new_y="NEXT")
    stats = metadata['stat_win_rate']
    if stats:
        pdf.write_html(stats)
    general_stats = get_generalstats(team)
    if general_stats:
        pdf.write_html(general_stats)

    # Replays
    pdf.cell(0, 5, f"Replays:", new_y="NEXT")
    pdf.set_font("helvetica", size=9)
    # Basic table:
    # replays_dire = {str(x) for x in metadata['replays_dire']}
    replays_dire = metadata['replays_dire']
    if replays_dire:
        replays_dire.sort(reverse=True)
    else:
        replays_dire = []
    replays_radiant = metadata['replays_radiant']
    if replays_radiant:
        replays_radiant.sort(reverse=True)
    else:
        replays_radiant = []

    with pdf.table() as table:
        row = table.row()
        row.cell("Dire")
        row.cell("Radiant")
        for dire, radiant in zip_longest(replays_dire, replays_radiant, fillvalue=''):
            row = table.row()
            row.cell(str(dire))
            row.cell(str(radiant))

    # Draft onlys
    drafts_only_dire = metadata['drafts_only_dire']
    if drafts_only_dire:
        drafts_dire = [x for x in drafts_only_dire if x not in replays_dire]
        drafts_dire.sort(reverse=True)
    else:
        drafts_dire = []

    drafts_only_radiant = metadata['drafts_only_radiant']
    if drafts_only_radiant:
        drafts_radiant = [x for x in drafts_only_radiant if x not in replays_radiant]
        drafts_radiant.sort(reverse=True)
    else:
        drafts_radiant = []

    if drafts_dire or drafts_radiant:
        pdf.set_font('helvetica', size=12)
        pdf.cell(40, 10, f"Drafts only:", new_y="NEXT")
        pdf.set_font("helvetica", size=9)
        with pdf.table() as table:
            row = table.row()
            row.cell("Dire")
            row.cell("Radiant")
            for dire, radiant in zip_longest(drafts_dire, drafts_radiant, fillvalue=''):
                row = table.row()
                row.cell(str(dire))
                row.cell(str(radiant))

    # Pick priority
    pick_priority = metadata.get('pick_priority')
    if pick_priority:
        pdf.add_page()
        pdf.image(Path(PLOT_BASE_PATH) / pick_priority, keep_aspect_ratio=True, w=180)
    # Draft summary + pick tables
    plot_draft_summary = metadata.get('plot_draft_summary')
    plot_picktables = metadata.get('plot_picktables')
    if plot_draft_summary and plot_picktables:
        pdf.add_page()
        pdf.image(Path(PLOT_BASE_PATH) / plot_draft_summary, y=0, keep_aspect_ratio=True, w=180)
        pdf.image(Path(PLOT_BASE_PATH) / plot_picktables, x=5, y=0.53*297, keep_aspect_ratio=True, w=200)
    # Hero Picks
    plot_hero_picks = metadata.get('plot_hero_picks')
    if plot_hero_picks:
        pdf.add_page()
        pdf.image(Path(PLOT_BASE_PATH) / plot_hero_picks, keep_aspect_ratio=True, w=180)
    plot_hero_picks_portrait = metadata.get('hero_picks_portrait')
    if plot_hero_picks_portrait:
        pdf.add_page()
        pdf.image(
            Path(PLOT_BASE_PATH) / plot_hero_picks_portrait,
            keep_aspect_ratio=True, y=5, w=180, h=290)
    # Hero Flex
    plot_hero_flex = metadata.get('plot_hero_flex')
    if plot_hero_flex:
        pdf.add_page()
        pdf.image(Path(PLOT_BASE_PATH) / plot_hero_flex, y=0, keep_aspect_ratio=True, w=180, h=290)
    # Flex pubs
    # plot_flex_pubs = metadata.get('plot_flex_pubs')
    # if plot_flex_pubs:
    #     pdf.add_page()
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_flex_pubs, y=0, keep_aspect_ratio=True, w=180, h=290)
    # Win Rate
    # plot_win_rate = metadata.get('plot_win_rate')
    # if plot_win_rate:
    #     pdf.add_page()
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_win_rate, keep_aspect_ratio=True, w=180)
    # First Pick Drafts
    # plot_drafts_first = metadata.get('plot_drafts_first')
    # if plot_drafts_first:
    #     pdf.add_page()
    #     pdf.set_font('helvetica', size=12)
    #     pdf.cell(0, 0, f"First pick drafts", new_x="LMARGIN", new_y="NEXT", align='C')
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_drafts_first[0], y=15, keep_aspect_ratio=True, w=180)
    #     for d in plot_drafts_first[1:]:
    #         pdf.add_page()
    #         pdf.image(Path(PLOT_BASE_PATH) / d, keep_aspect_ratio=True, w=180)
    # # Second Pick Drafts
    # plot_drafts_second = metadata.get('plot_drafts_second')
    # if plot_drafts_second:
    #     pdf.add_page()
    #     pdf.set_font('helvetica', size=12)
    #     pdf.cell(0, 0, f"Second pick drafts", new_x="LMARGIN", new_y="NEXT", align='C')
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_drafts_second[0], y=15, keep_aspect_ratio=True, w=180)
    #     for d in plot_drafts_second[1:]:
    #         pdf.add_page()
    #         pdf.image(Path(PLOT_BASE_PATH) / d, keep_aspect_ratio=True, w=180)
    plot_drafts_all = metadata.get('plot_drafts_all')
    if plot_drafts_all:
        pdf.add_page()
        pdf.set_font('helvetica', size=12)
        pdf.cell(0, 0, f"Drafts", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.image(Path(PLOT_BASE_PATH) / plot_drafts_all[0], y=15, keep_aspect_ratio=True, w=180)
        for d in plot_drafts_all[1:]:
            pdf.add_page()
            pdf.image(Path(PLOT_BASE_PATH) / d, keep_aspect_ratio=True, w=180)

    # Write pdf
    pdf.output(output)
    metadata['pdf_report'] = str(output)


def make_mini_report(team: TeamInfo, metadata: dict, output: Path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 24)
    dataset = nice_time_names.get(metadata['name'], metadata['name'])
    time_string = metadata.get('time_string', "(No replay data)")
    pdf.multi_cell(0, 10, f"{team.name} {time_string}, {dataset}", align="c", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', size=12)
    # Stats
    pdf.cell(0, 5, f"Win rates:", new_x="LMARGIN", new_y="NEXT")
    stats = metadata['stat_win_rate']
    if stats:
        pdf.write_html(stats)
    general_stats = get_generalstats(team)
    if general_stats:
        pdf.write_html(general_stats)

    # Replays
    pdf.cell(0, 5, f"Replays:", new_y="NEXT")
    pdf.set_font("helvetica", size=9)
    # Basic table:
    # replays_dire = {str(x) for x in metadata['replays_dire']}
    replays_dire = metadata['replays_dire']
    if replays_dire:
        replays_dire.sort(reverse=True)
    else:
        replays_dire = []
    replays_radiant = metadata['replays_radiant']
    if replays_radiant:
        replays_radiant.sort(reverse=True)
    else:
        replays_radiant = []

    with pdf.table() as table:
        row = table.row()
        row.cell("Dire")
        row.cell("Radiant")
        for dire, radiant in zip_longest(replays_dire, replays_radiant, fillvalue=''):
            row = table.row()
            row.cell(str(dire))
            row.cell(str(radiant))

    # Draft onlys
    drafts_only_dire = metadata['drafts_only_dire']
    if drafts_only_dire:
        drafts_dire = [x for x in drafts_only_dire if x not in replays_dire]
        drafts_dire.sort(reverse=True)
    else:
        drafts_dire = []

    drafts_only_radiant = metadata['drafts_only_radiant']
    if drafts_only_radiant:
        drafts_radiant = [x for x in drafts_only_radiant if x not in replays_radiant]
        drafts_radiant.sort(reverse=True)
    else:
        drafts_radiant = []

    if drafts_dire or drafts_radiant:
        pdf.set_font('helvetica', size=12)
        pdf.cell(40, 10, f"Drafts only:", new_y="NEXT")
        pdf.set_font("helvetica", size=9)
        with pdf.table() as table:
            row = table.row()
            row.cell("Dire")
            row.cell("Radiant")
            for dire, radiant in zip_longest(drafts_dire, drafts_radiant, fillvalue=''):
                row = table.row()
                row.cell(str(dire))
                row.cell(str(radiant))

    # Pick priority
    # pick_priority = metadata.get('pick_priority')
    # if pick_priority:
    #     pdf.add_page()
    #     pdf.image(Path(PLOT_BASE_PATH) / pick_priority, keep_aspect_ratio=True, w=180)
    # # Draft summary + pick tables
    # plot_draft_summary = metadata.get('plot_draft_summary')
    # plot_picktables = metadata.get('plot_picktables')
    # if plot_draft_summary or plot_picktables:
    #     pdf.add_page()
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_draft_summary, y=0, keep_aspect_ratio=True, w=180)
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_picktables, x=5, y=0.53*297, keep_aspect_ratio=True, w=200)
    # Hero Picks
    # plot_hero_picks = metadata.get('plot_hero_picks')
    # plot_hero_picks = metadata.get('plot_hero_picks')
    # if plot_hero_picks:
    #     pdf.add_page()
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_hero_picks, keep_aspect_ratio=True, w=180)
    plot_hero_picks_portrait = metadata.get('hero_picks_portrait')
    if plot_hero_picks_portrait:
        pdf.add_page()
        pdf.image(
            Path(PLOT_BASE_PATH) / plot_hero_picks_portrait,
            keep_aspect_ratio=True, y=5, w=180, h=290)
    # Hero Flex
    plot_hero_flex = metadata.get('plot_hero_flex')
    if plot_hero_flex:
        pdf.add_page()
        pdf.image(Path(PLOT_BASE_PATH) / plot_hero_flex, keep_aspect_ratio=True, w=180, h=290)
    # Win Rate
    # plot_win_rate = metadata.get('plot_win_rate')
    # if plot_win_rate:
    #     pdf.add_page()
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_win_rate, keep_aspect_ratio=True, w=180)
    # First Pick Drafts
    # plot_drafts_first = metadata.get('plot_drafts_first')
    # if plot_drafts_first:
    #     pdf.add_page()
    #     pdf.set_font('helvetica', size=12)
    #     pdf.cell(0, 0, f"First pick drafts", new_x="LMARGIN", new_y="NEXT", align='C')
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_drafts_first[0], y=15, keep_aspect_ratio=True, w=180)
    #     for d in plot_drafts_first[1:]:
    #         pdf.add_page()
    #         pdf.image(Path(PLOT_BASE_PATH) / d, keep_aspect_ratio=True, w=180)
    # # Second Pick Drafts
    # plot_drafts_second = metadata.get('plot_drafts_second')
    # if plot_drafts_second:
    #     pdf.add_page()
    #     pdf.set_font('helvetica', size=12)
    #     pdf.cell(0, 0, f"Second pick drafts", new_x="LMARGIN", new_y="NEXT", align='C')
    #     pdf.image(Path(PLOT_BASE_PATH) / plot_drafts_second[0], y=15, keep_aspect_ratio=True, w=180)
    #     for d in plot_drafts_second[1:]:
    #         pdf.add_page()
    #         pdf.image(Path(PLOT_BASE_PATH) / d, keep_aspect_ratio=True, w=180)
    plot_drafts_all = metadata.get('plot_drafts_all')
    if plot_drafts_all:
        pdf.add_page()
        pdf.set_font('helvetica', size=12)
        pdf.cell(0, 0, f"Drafts", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.image(Path(PLOT_BASE_PATH) / plot_drafts_all[0], y=15, keep_aspect_ratio=True, w=180)
        for d in plot_drafts_all[1:]:
            pdf.add_page()
            pdf.image(Path(PLOT_BASE_PATH) / d, keep_aspect_ratio=True, w=180)

    # Write pdf
    pdf.output(output)
    metadata['pdf_mini_report'] = str(output)


def process_team(team: TeamInfo, metadata, time: datetime,
                 args: argparse.Namespace, end_time: datetime = None, extra_replay_list=None,
                 scrim_list=None):

    if len(team.players) != 5:
        LOG.error(f"Team {team.name} ({team.team_id}) has incorrect number of players ({len(team.players)})! Skipping!")
        return

    reprocess = args.reprocess
    extra_stackid = args.extra_stackid
    stat_time = ti if (ti := ImportantTimes.get(args.statistic_time)) is not None else time

    if extra_stackid is not None:
        team.extra_stackid = extra_stackid
    if end_time is not None:
        r_filter = Replay.endTimeUTC.between(time, end_time)
    else:
        r_filter = Replay.endTimeUTC >= time

    if extra_replay_list is not None:
        r_filter = and_(Replay.replayID.in_(extra_replay_list), r_filter)

    r_filter = and_(Replay.replayID.not_in([8178449560,]),
                    r_filter)
    try:
        r_query = team.get_replays(session).filter(r_filter)
    except SQLAlchemyError as e:
        LOG.opt(exception=True).error("Failed to retrieve replays for team {}".format(team.name))
        quit()

    # start = t.process_time()
    new_dire, dire_list = is_updated(session, r_query, team, Team.DIRE,
                                     metadata.get('replays_dire'), is_full_replay)
    new_radiant, radiant_list = is_updated(session, r_query, team, Team.RADIANT,
                                           metadata.get('replays_radiant'), is_full_replay)

    new_draft_dire, dire_drafts = is_updated(session, r_query, team, Team.DIRE,
                                     metadata.get('drafts_only_dire'), has_picks)
    new_draft_radiant, radiant_drafts = is_updated(session, r_query, team, Team.RADIANT,
                                     metadata.get('drafts_only_radiant'), has_picks)

    try:
        last_update_time = datetime.fromtimestamp(metadata['last_update_time'])
    except KeyError:
        last_update_time = datetime.now() - timedelta(days=30)
    pub_update_time = get_team_last_result(team, pub_session)
    if pub_update_time is BAD_TEAM_TIME_SENTINEL:
        pubs_updated = False
    else:
        pubs_updated = pub_update_time > last_update_time
        pubs_updated = True
    if reprocess:
        if r_query.count() != 0:
            new_dire = True
            new_radiant = True
            new_draft_radiant = True
            new_draft_dire = True
        elif extra_replay_list is not None:
            LOG.info(f"Could not reprocess scrims for {team.name}, no replays found in list:")
        # Still do pubs!
        pubs_updated = True
    # Disable pubs for forseeable future
    pubs_updated = args.pubs_updated
    if not new_dire and not new_radiant and not new_draft_dire and not new_draft_radiant:
        LOG.info("No new updates for {}".format(team.name))
        if pubs_updated:
            if metadata['name'] == 'Scrims' and r_query.count() == 0:
                LOG.debug("Skipping forced pubs for zero replay Scrims dataset.")
                return metadata
            LOG.debug("Pub data update true, remaking hero picks.")
            # No need to do limit plots as they are without pubs.
            # metadata = do_player_picks(team, metadata, r_filter, mintime=stat_time, maxtime=end_time)
            # metadata = do_flex_pubs(team, metadata, time, end_time)
            pub_bar = tqdm(total=3, position=2, desc='Portrait Picks', leave=False)
            metadata = do_portrait_picks(team, metadata, r_query, min_time=time)
            pub_bar.update()
            pub_bar.set_description('Reports')
            metadata['last_update_time'] = datetime.timestamp(datetime.now())
            path = store_metadata(team, metadata)
            LOG.debug("Metadata file updated at {}".format(str(path)))
            plt.close('all')

            LOG.debug("Making PDF report.")
            report_path = Path(PLOT_BASE_PATH) / team.name / metadata['name'] / f"{team.name}_{metadata['name']}.pdf"
            mini_report_path = Path(PLOT_BASE_PATH) / team.name / metadata['name'] / f"{team.name}_{metadata['name']}_mini.pdf"
            make_report(team, metadata, report_path)
            pub_bar.update()
            make_mini_report(team, metadata, mini_report_path)
            pub_bar.update()

            path = store_metadata(team, metadata)
            LOG.debug("Metadata file updated at {}".format(str(path)))

            return metadata

        return metadata

    metadata['replays_dire'] = list(dire_list)
    metadata['drafts_only_dire'] = list(dire_drafts)
    metadata['replays_radiant'] = list(radiant_list)
    metadata['drafts_only_radiant'] = list(radiant_drafts)
    LOG.debug(f'Dire replays: {dire_list}')
    LOG.debug(f'Radiant replays: {radiant_list}')

    metadata['last_update_time'] = datetime.timestamp(datetime.now())
    # A nice string for the time
    metadata['time_string'] = f"From {time.astimezone(pytz.timezone('CET')).strftime('%Y-%m-%d')}"
    if end_time is not None:
        metadata['time_string'] += f" to {end_time.astimezone(pytz.timezone('CET')).strftime('%Y-%m-%d')}"

    LOG.debug("Process {}.".format(team.name))
    tp_bar = tqdm(total=12, position=2, desc='Draft', leave=False)
    if args.draft:
        plt.close('all')
        start = t.process_time()
        metadata = do_draft(
            team, metadata, new_draft_dire, new_draft_radiant,
            r_filter, scrim_list=scrim_list)
        plt.close('all')
        LOG.debug(f"Processed drafts in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Positioning')
    if args.positioning:
        start = t.process_time()
        metadata = do_positioning(team, r_query,
                                  -2*60, 10*60,
                                  metadata,
                                  new_dire, new_radiant
                                  )
        plt.close('all')
        LOG.debug(f"Processed positioning in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Wards')
    if args.wards:
        start = t.process_time()
        metadata = do_wards(team, r_query, metadata, new_dire, new_radiant)
        plt.close('all')
        LOG.debug(f"Processed wards in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Individual Wards')
    if args.wards_separate:
        LOG.debug("Processing individual ward replays.")
        start = t.process_time()
        metadata = do_wards_separate(team, r_query, metadata, new_dire,
                                    new_radiant)
        plt.close('all')
        LOG.debug(f"Processed in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Positioning')
    if args.pregame_positioning:
        start = t.process_time()
        metadata = do_pregame_routes(team, r_query, metadata, new_dire,
                                     new_radiant, cache=True)
        plt.close('all')
        LOG.debug(f"Processed positioning in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Smoke')
    if args.smoke:
        start = t.process_time()
        metadata = do_smoke(team, r_query, metadata, new_dire, new_radiant)
        plt.close('all')
        LOG.debug(f"Processed smoke in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Scans')
    if args.scans:
        start = t.process_time()
        metadata = do_scans(team, r_query, metadata, new_dire, new_radiant)
        plt.close('all')
        LOG.debug(f"Processed scans in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Runes')
    if args.runes:
        start = t.process_time()
        # Needed due to parallel plotting
        with matplotlib.rc_context({'figure.max_open_warning': 0}):
            metadata = do_runes(
                team, r_query, metadata, new_dire, new_radiant, reprocess=args.reprocess
                )
        plt.close('all')
        LOG.debug(f"Processed runes in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Tormentors')
    if args.tormentors:
        start = t.process_time()
        metadata = do_tormentor_routes(
            team, r_query, metadata, new_dire,
            new_radiant, cache=True)
        plt.close('all')
        LOG.debug(f"Processed tormentors in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Summary')
    if args.summary:
        start = t.process_time()
        metadata = do_summary(team, r_query, metadata, r_filter)
        metadata = do_summary(team, r_query, metadata, r_filter, limit=5, postfix="limit5")
        # metadata = do_summary(team, l_query, metadata, r_filter, postfix="limit5")
        LOG.debug(f"Processed summary in {t.process_time() - start}")
        start = t.process_time()
        metadata = do_player_picks(team, metadata, r_filter, mintime=stat_time, maxtime=end_time)
        metadata = do_player_picks(team, metadata, r_filter, limit=5, postfix="limit5",
                                   mintime=stat_time, maxtime=end_time)
        LOG.debug(f"Processed player picks in {t.process_time() - start}")
        # metadata = do_flex_pubs(team, metadata, time, end_time)
        start = t.process_time()
        metadata = do_portrait_picks(team, metadata, r_query, min_time=time)
        LOG.debug(f"Processed portrait picks in {t.process_time() - start}")
        start = t.process_time()
        metadata = do_stacks(team, r_query, metadata)
        LOG.debug(f"Processed stacks in {t.process_time() - start}")
        plt.close('all')
    tp_bar.update()
    tp_bar.set_description('Priority Picks')
    if args.prioritypicks:
        if new_dire or new_radiant:
            start = t.process_time()
            metadata = do_priority_picks(team, r_query, metadata)
            plt.close('all')
            LOG.debug(f"Processed priority picks in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Counters')
    if args.counters:
        if new_dire or new_radiant:
            start = t.process_time()
            metadata = do_counters(team, r_query, metadata)
            LOG.debug(f"Processed counter picks in {t.process_time() - start}")
    tp_bar.update()
    tp_bar.set_description('Reports and misc')
    start = t.process_time()
    metadata['stat_win_rate'] = do_statistics(team, r_query)
    LOG.debug(f"Processed statistics in {t.process_time() - start}")

    LOG.debug("Making PDF report.")
    report_path = Path(PLOT_BASE_PATH) / team.name
    report_path = Path(PLOT_BASE_PATH) / team.name / metadata['name'] / f"{team.name}_{metadata['name']}.pdf"
    mini_report_path = Path(PLOT_BASE_PATH) / team.name / metadata['name'] / f"{team.name}_{metadata['name']}_mini.pdf"
    make_report(team, metadata, report_path)
    make_mini_report(team, metadata, mini_report_path)

    path = store_metadata(team, metadata)

    LOG.debug("Metadata file updated at {}".format(str(path)))
    tp_bar.update()

    return metadata


def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team


def do_datasummary(r_filter=None):
    # Wards
    LOG.debug("Processing ward win rates for dataset.")
    w_filter = (Ward.ward_type == WardType.OBSERVER,)
    if r_filter is not None:
        w_filter = (*w_filter, *r_filter)

    w_query = session.query(Ward.game_time, Ward.xCoordinate,
                            Ward.yCoordinate, Ward.winner)\
        .filter(and_(*w_filter))

    time_binning = [(0, 10*60), (10*60, 20*60), (20*60, 30*60),
                    (30*60, 400*60)]
    #t_binning = interval_range(0, 30*60, 3)
    time_binning = IntervalIndex.from_tuples(time_binning)
    ward_bins = 16
    spacial_binning = [float(x)/ward_bins for x in range(ward_bins)]

    def _team_wards(ward_team: Team):
        team_wards = w_query.filter(Ward.team == ward_team)
        try:
            ward_frame = read_sql(team_wards.statement, session.bind)
        except SQLAlchemyError as e:
            LOG.opt(exception=True).error("Failed to retrieve replays for filter {}".format(w_filter))
            quit()

        ward_frame['tbin'] = IntervalIndex(cut(ward_frame['game_time'],
                                               time_binning, right=True))
        ward_frame['xbin'] = IntervalIndex(cut(ward_frame['xCoordinate'],
                                               spacial_binning)).mid
        ward_frame['ybin'] = IntervalIndex(cut(ward_frame['yCoordinate'],
                                           spacial_binning)).mid
        ward_count = ward_frame.groupby(['tbin', 'xbin', 'ybin'])[["winner"]]\
                               .count()
        ward_count = ward_count.reset_index()
        ward_sum = ward_frame.groupby(['tbin', 'xbin', 'ybin'])[["winner"]]\
                             .sum()
        ward_sum = ward_sum.reset_index()
        ward_mean = ward_frame.groupby(['tbin', 'xbin', 'ybin'])[["winner"]]\
                              .mean()
        ward_mean = ward_mean.reset_index()

        summary = DataFrame({
            'x': ward_count['xbin'],
            'y': ward_count['ybin'],
            't': ward_count['tbin'],
            'mean': ward_mean['winner'],
            'wins': ward_sum['winner'],
            'total': ward_count['winner']
        })

        return summary

    dire_summary = _team_wards(Team.DIRE)
    radiant_summary = _team_wards(Team.RADIANT)

    def _plot_wards_summary(query_data: DataFrame, weights: str, ax_in=None):
        if ax_in is None:
            fig, ax_in = plt.subplots(figsize=(10, 10))
        else:
            fig = plt.gcf()

        plot = ax_in.hexbin(x=query_data['x'],
                            y=query_data['y'],
                            C=query_data[weights],
                            gridsize=ward_bins, 
                            #mincnt=1,
                            #extent=[0, 1, 0, 1],
                            cmap='cool',
                            zorder=2)
        ax_in.set_xlim([0,1])
        ax_in.set_ylim([0,1])
        # Add map
        img = mpimg.imread(StaticAnalysis.CONFIG['images']['MAP_PATH'])
        ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
        ax_in.axis('off')

        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot, cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

        return fig, ax_in

    def _ward_summary(data: DataFrame, weights: str='mean'):
        fig, axList = plt.subplots(2,2, figsize=(8,6))

        data_in = data.loc[(data['t'] == time_binning[0]) & (data['total'] > 10)]
        _, ax = _plot_wards_summary(data_in, weights=weights, ax_in=axList[0,0])
        ax.set_title("0 to 10min")

        data_in = data.loc[(data['t'] == time_binning[1]) & (data['total'] > 10)]
        _, ax = _plot_wards_summary(data_in, weights=weights, ax_in=axList[0,1])
        ax.set_title("10 to 20min")

        data_in = data.loc[(data['t'] == time_binning[2]) & (data['total'] > 10)]
        _, ax = _plot_wards_summary(data_in, weights=weights, ax_in=axList[1,0])
        ax.set_title("20 to 30min")

        data_in = data.loc[(data['t'] == time_binning[3]) & (data['total'] > 10)]
        _, ax = _plot_wards_summary(data_in, weights=weights, ax_in=axList[1,1])
        ax.set_title("30+mins")

        return fig, axList

    data_plot_dir = Path(StaticAnalysis.CONFIG['output']['DATA_SUMMARY_OUTPUT'])
    fig, ax = _ward_summary(dire_summary)
    fig.tight_layout()
    fig.savefig(data_plot_dir / 'wards_dire.png')
    plt.close(fig)

    fig, ax = _ward_summary(radiant_summary)
    fig.tight_layout()
    fig.savefig(data_plot_dir / 'wards_radiant.png')
    plt.close(fig)



def main(arguments):
    plt.ioff()
    args = arguments.parse_args()
    LOG.debug(args)
    # TIME_CUT = [ImportantTimes['PreviousMonth'], ]
    TIME_CUT = {}
    END_TIME = []

    if args.use_time is not None:
        for time in args.use_time:
            try:
                TIME_CUT[time] = ImportantTimes[time]
            except ValueError:
                LOG.info("--use_time must correspond to a time in ImportantTimes:")
                LOG.info(*(k for k in ImportantTimes.keys()))
                exit()
    if args.custom_time is not None:
        TIME_CUT = {"custom": datetime.utcfromtimestamp(args.custom_time),}
    # Ensure that if we have time limits we have the correct number.
    if args.end_time is not None:
        for time in args.end_time:
            if time not in ImportantTimes:
                LOG.info("--end_time must correspond to a time in ImportantTimes:")
                LOG.info(*(k for k in ImportantTimes.keys()))
                exit()
            END_TIME.append(ImportantTimes[time])
    else:
        END_TIME = [None] * len(TIME_CUT)

    if len(END_TIME) != len(TIME_CUT):
        LOG.info("If defined --end_time must have an end time for all --use_time and the custom time if set.")
        LOG.info(f"{args.end_time}")
        LOG.info(f"{args.use_time} + {args.custom_time}")
        exit()

    if args.scrim_endtime is not None:
        if args.scrim_endtime not in ImportantTimes:
            LOG.info("--end_time must correspond to a time in ImportantTimes:")
            LOG.info(*(k for k in ImportantTimes.keys()))
            exit()
    # if args.use_dataset:
    #     data_set_name = args.use_dataset
    # elif args.use_time:
    #     data_set_name = args.use_time
    # else:
    #     data_set_name = "default"

    default_process = not args.default_off
    if args.draft is None:
        args.draft = default_process
    if args.positioning is None:
        args.positioning = default_process
    if args.wards is None:
        args.wards = default_process
    if args.wards_separate is None:
        args.wards_separate = default_process
    if args.pregame_positioning is None:
        args.pregame_positioning = default_process
    if args.smoke is None:
        args.smoke = default_process
    if args.scans is None:
        args.scans = default_process
    if args.summary is None:
        args.summary = default_process
    if args.counters is None:
        args.counters = default_process
    if args.prioritypicks is None:
        args.prioritypicks = default_process
    if args.runes is None:
        args.runes = default_process
    if args.tormentors is None:
        args.tormentors = default_process

    scims_json = StaticAnalysis.CONFIG['scrims']['SCRIMS_JSON']
    try:
        with open(scims_json) as file:
            SCRIM_REPLAY_DICT = json.load(file)
    except IOError:
        LOG.opt(exception=True).error(f"Failed to read scrim_list {scims_json}")
        raise

    if args.process_teams is not None:
        for proc_team in (team_bar := tqdm(args.process_teams, position=0, desc='Team')):
            if args.extra_stackid is not None and len(args.process_teams) > 1:
                LOG.error("Extra stack id only supported with one team.")
                exit()
            team = get_team(proc_team)
            if team is None:
                LOG.error("Unable to find team {} in database!"
                      .format(proc_team))
                continue
            team_bar.set_description(team.name)

            if args.statistic_time:
                # Add scrims if we have them
                scrim_list = []
                if args.scrim_time and team is not None:
                    team_scrims = SCRIM_REPLAY_DICT.get(str(team.team_id))
                    if team_scrims:
                        scrim_list = list(team_scrims.keys())

                if args.statistic_time in nice_time_names:
                    time_name = nice_time_names[args.statistic_time]
                else:
                    time_name = args.statistic_time
                stat_string = f"Data set - {time_name}<br>\n"
                stat_string += do_general_stats(team, ImportantTimes[args.statistic_time],
                                                args, replay_list=scrim_list)
                store_generalstats(team, stat_string)

            team_scrims = SCRIM_REPLAY_DICT.get(str(team.team_id))
            if team_scrims is not None:
                scrim_list = list(team_scrims.keys())
            else:
                scrim_list = None

            for time, end in (ttime_bar := tqdm(
                list(zip(TIME_CUT, END_TIME)), position=1, desc='Time', leave=False)):
                data_set_name = time
                metadata = get_create_metadata(team, data_set_name)
                ttime_bar.set_description(f'Time {time}')
                LOG.debug(f'{team.name} ({time})')
                metadata['time_cut'] = TIME_CUT[time].timestamp()

                process_team(team, metadata, TIME_CUT[time], args, end_time=end,
                             scrim_list=scrim_list)

            if args.scrim_time:
                done_scrims = True

                if team_scrims is None:
                    LOG.info(f"No scrims for {team.name}. Skipping.")
                else:
                    end_time = None
                    if args.scrim_endtime is not None:
                        end_time = ImportantTimes[args.scrim_endtime]
                    metadata = get_create_metadata(team, "Scrims")
                    metadata['time_cut'] = ImportantTimes[args.scrim_time].timestamp()
                    team_bar.set_description(f'{team.name} (Scrims @ {args.scrim_time})')
                    LOG.debug(f'{team.name} (Scrims @ {args.scrim_time}')
                    process_team(team, metadata, ImportantTimes[args.scrim_time],
                                 args, end_time=end_time, extra_replay_list=scrim_list,
                                 scrim_list=scrim_list)

    if args.process_all:
        for team in team_session.query(TeamInfo):
            metadata = get_create_metadata(team, data_set_name)
            metadata['time_cut'] = TIME_CUT.timestamp()
            process_team(team, metadata, TIME_CUT, args)

    # if not args.skip_datasummary:
    #     do_datasummary()

if __name__ == "__main__":
    with logging_redirect_tqdm():
        main(arguments)