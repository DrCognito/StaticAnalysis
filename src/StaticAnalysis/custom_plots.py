import time as t
from argparse import ArgumentParser
from datetime import datetime, timedelta
from itertools import zip_longest
from os import environ as environment
from os import mkdir
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
from fpdf import FPDF
from sqlalchemy import and_, or_
from sqlalchemy.orm import sessionmaker

from StaticAnalysis.analysis.Player import player_positioning_single
from StaticAnalysis.analysis.route_vis import plot_pregame_sing
from StaticAnalysis.analysis.visualisation import (dataframe_xy,
                                                   get_binning_percentile_xy,
                                                   plot_object_position)
from StaticAnalysis.lib.team_info import InitTeamDB, TeamInfo, TeamPlayer
from StaticAnalysis.replays.Player import PlayerStatus
from StaticAnalysis.replays.Replay import InitDB, Replay

DB_PATH = environment['PARSED_DB_PATH']
PLOT_BASE_PATH = environment['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()


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
            post_fix = 'heatmap.png'
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
            post_fix = 'route.png'
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
    plots = []
    # Get individual ones
    p1: TeamPlayer
    p2: TeamPlayer
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
            plots.append(output)

    pdf = FPDF()
    for i, j in zip_longest(plots[0:-1:2], plots[1::2]):
        pdf.add_page()
        pdf.image(i, keep_aspect_ratio=True, w=180)
        if j is not None:
            pdf.image(j, keep_aspect_ratio=True, w=180)
    pdf.output(report_output)


def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team


if __name__ == '__main__':
    team_og = get_team(2586976)
    team_liquid = get_team(2163)
    team_gaimin = get_team(8599101)
    teams = [team_gaimin,]
    replay_ids = [7330464651,]

    for te, i in zip(teams, replay_ids):
        player_heatmap_report(session, i, te)
        player_route_report(session, i, te)

    # do_comparison_report(session, [7254795299, 7256414790], [team_og, team_liquid])