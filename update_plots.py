import json
from argparse import ArgumentParser
from datetime import datetime
from os import environ as environment
from os import mkdir
from pathlib import Path

import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from analysis.draft_vis import replay_draft_image
from analysis.Player import (cumulative_player, pick_context, player_heroes,
                             player_position)
from analysis.Replay import (draft_summary, get_ptbase_tslice, get_smoke,
                             hero_win_rate, pair_rate, win_rate_table,
                             get_rune_control)
from analysis.visualisation import (dataframe_xy, dataframe_xy_time,
                                    dataframe_xy_time_smoke,
                                    plot_draft_summary, plot_hero_winrates,
                                    plot_map_points, plot_object_position,
                                    plot_object_position_scatter,
                                    plot_pick_context, plot_pick_pairs,
                                    plot_player_heroes,
                                    plot_player_positioning,
                                    plot_runes)
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from lib.important_times import ImportantTimes
from lib.metadata import is_updated, make_meta
from lib.team_info import InitTeamDB, TeamInfo
from replays.Player import Player, PlayerStatus
from replays.Replay import InitDB, Replay, Team
from replays.Rune import Rune
from replays.Scan import Scan
from replays.Smoke import Smoke
from replays.TeamSelections import TeamSelections
from replays.Ward import Ward, WardType

load_dotenv(dotenv_path="setup.env")
DB_PATH = environment['PARSED_DB_PATH']
PLOT_BASE_PATH = environment['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()

TIME_CUT = ImportantTimes['PreviousTriMonth']

arguments = ArgumentParser()
arguments.add_argument('--process_teams',
                       help='''Process specific team.''',
                       nargs='+')
arguments.add_argument('--using_leagues',
                       help='''Use replays only from these league ids.''',
                       nargs='*')
arguments.add_argument('--use_dataset',
                       help='''Use this or create a new dataset
                               for these options.''',
                       default='default')
arguments.add_argument('--reprocess',
                       help='''Remake plots regardless of metadata''',
                       action='store_true')
arguments.add_argument('--use_time',
                       help='''Specify a time from lib.important_times
                               to use for cut.''')
arguments.add_argument('--custom_time',
                       help='''Specity a unix time to over-ride time cut.''',
                       type=int)


def get_create_metadata(team: TeamInfo, dataset="default"):
    team_path = Path(PLOT_BASE_PATH) / team.name
    dataset_path = team_path / dataset
    if not team_path.exists():
        print("Adding new team {}.".format(team.name))
        mkdir(team_path)
        mkdir(dataset_path)
        mkdir(dataset_path / 'dire')
        mkdir(dataset_path / 'radiant')
    
    meta_json = team_path / 'meta_data.json'
    if meta_json.exists():
        with open(meta_json, 'r') as file:
            json_file = json.load(file)
        if dataset in json_file:
            return json_file[dataset]

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


def do_positioning(team: TeamInfo, r_query,
                   start: int, end: int,
                   metadata: dict,
                   update_dire=True, update_radiant=True,
                   positions=(0, 1, 2, 3, 4)):
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
    if update_dire:
        metadata['plot_pos_radiant'] = []
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    for pos in positions:
        if pos >= len(team.players):
            print("Position {} is out of range for {}"
                  .format(pos, team.name))
        p_name = team.players[pos].name
        metadata['player_names'].append(p_name)
        print("Processing {} for {}".format(p_name, team.name))
        pos_dire, pos_radiant = player_position(session, r_query, team,
                                                player_slot=pos,
                                                start=start, end=end)

        if update_dire:
            if pos_dire.count() == 0:
                print("No data for {} on Dire.".format(team.players[pos].name))
                continue
            output = team_path / 'dire' / (p_name + '.png')
            dire_ancient_filter = location_filter(dire_ancient_cords,
                                                  PlayerStatus)
            pos_dire = pos_dire.filter(dire_ancient_filter)
            fig, ax = plot_player_positioning(dataframe_xy(pos_dire,
                                                           PlayerStatus,
                                                           session))
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata['plot_pos_dire'].append(relpath)

        if update_radiant:
            if pos_radiant.count() == 0:
                print("No data for {} on Radiant.".format(team.players[pos].name))
                continue
            output = team_path / 'radiant' / (p_name + '.png')
            ancient_filter = location_filter(radiant_ancient_cords,
                                             PlayerStatus)
            pos_radiant = pos_radiant.filter(ancient_filter)
            fig, ax = plot_player_positioning(dataframe_xy(pos_radiant,
                                                           PlayerStatus,
                                                           session))
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata['plot_pos_radiant'].append(relpath)

    return metadata


def do_draft(team: TeamInfo, metadata,
             update_dire=True, update_radiant=True):
    '''Produces draft images from the replays in r_query.
       Will only proceed for sides with update = True.
    '''
    if not update_dire and not update_radiant:
        return metadata

    t_filter = team.filter
    r_drafted = session.query(Replay).filter(t_filter)\
                                     .outerjoin(TeamSelections)\
                                     .filter(TeamSelections.draft.any())

    dire_filter = Replay.get_side_filter(team, Team.DIRE)
    radiant_filter = Replay.get_side_filter(team, Team.RADIANT)
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']

    if update_dire:
        output = team_path / 'dire/drafts.png'
        dire_drafts = replay_draft_image(r_drafted.filter(dire_filter).all(),
                                         Team.DIRE,
                                         team.name)
        dire_drafts.save(output)
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_dire_drafts'] = relpath

    if update_radiant:
        output = team_path / 'radiant/drafts.png'
        radiant_drafts = replay_draft_image(r_drafted.filter(radiant_filter).all(),
                                            Team.RADIANT,
                                            team.name)
        radiant_drafts.save(output)
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_radiant_drafts'] = relpath

    return metadata


def do_wards(team: TeamInfo, r_query,
             metadata: dict,
             update_dire=True, update_radiant=True):

    if not update_dire and not update_radiant:
        return metadata
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    vmin, vmax = (1, None)

    wards_dire, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                                  Type=Ward,
                                                  start=-2*60, end=10*60)
    wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
    wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)
    metadata['plot_ward_names'] = ["Pregame", "0 to 4 mins", "4 to 8 mins"]
    if update_dire:
        metadata['plot_ward_dire'] = []
        output = team_path / 'dire'
        ward_df = dataframe_xy_time(wards_dire, Ward, session)

        fig, _ = plot_object_position(ward_df.loc[ward_df['game_time'] <= 0],
                                      vmin=vmin, vmax=vmax)
        fig.tight_layout()
        p_out = output / 'wards_pregame.png'
        fig.savefig(p_out)
        relpath = p_out.relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 0) &
                                                  (ward_df['game_time'] <= 4*60)],
                                      vmin=vmin, vmax=vmax)
        fig.tight_layout()
        p_out = output / 'wards_0to4.png'
        fig.savefig(p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 4*60) &
                                                  (ward_df['game_time'] <= 8*60)],
                                      vmin=vmin, vmax=vmax)
        fig.tight_layout()
        p_out = output / 'wards_4to8.png'
        fig.savefig(p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_dire'].append(str(relpath))

    if update_radiant:
        metadata['plot_ward_radiant'] = []
        output = team_path / 'radiant'
        ward_df = dataframe_xy_time(wards_radiant, Ward, session)

        fig, _ = plot_object_position(ward_df.loc[ward_df['game_time'] <= 0],
                                      vmin=vmin, vmax=vmax)
        fig.tight_layout()
        p_out = output / 'wards_pregame.png'
        fig.savefig(p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_radiant'].append(str(relpath))

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 0) &\
                                                  (ward_df['game_time'] <= 4*60)],
                                      vmin=vmin, vmax=vmax)
        fig.tight_layout()
        p_out = output / 'wards_0to4.png'
        fig.savefig(p_out)
        relpath = (p_out).relative_to(Path(PLOT_BASE_PATH))
        metadata['plot_ward_radiant'].append(str(relpath))

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 4*60) &
                                                  (ward_df['game_time'] <= 8*60)],
                                      vmin=vmin, vmax=vmax)
        fig.tight_layout()
        p_out = output / 'wards_4to8.png'
        fig.savefig(p_out)
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
    time_pairs = [
        (-10*60, 10*60),
        (10*60, 20*60),
        (20*60, 30*60),
        (30*60, 40*60),
        (40*60, 500*60)
    ]

    vmin, vmax = (1, None)

    time_titles = [
        'Pre-Game to 10 mins',
        '10 mins to 20 mins',
        '20 mins to 30 mins',
        '30 mins to 40 mins',
        '40 mins+'
    ]
    s_dire, s_radiant = get_smoke(r_query, session, team)

    def _plot_time_slice(times, title, data, axis):
        data_slice = data.loc[(data['game_start_time'] > times[0]) &
                              (data['game_start_time'] <= times[1])]
        plot_object_position(data_slice, bins=16, ax_in=axis,
                             vmin=vmin, vmax=vmax)
        axis.set_title(title)

    def _process_side(query, side: Team):
        data = dataframe_xy_time_smoke(query, Smoke, session)

        fig, axList = plt.subplots(3, 2, figsize=(8, 10))
        ((ax1, ax2), (ax3, ax4), (ax5, ax6)) = axList
        _plot_time_slice(time_pairs[0], time_titles[0], data, ax1)
        _plot_time_slice(time_pairs[1], time_titles[1], data, ax2)
        _plot_time_slice(time_pairs[2], time_titles[2], data, ax3)
        _plot_time_slice(time_pairs[3], time_titles[3], data, ax4)
        _plot_time_slice(time_pairs[4], time_titles[4], data, ax5)
        ax6.axis('off')

        team_str = 'dire' if side == Team.DIRE else 'radiant'
        output = team_path / '{}/smoke_summary.png'.format(team_str)
        fig.tight_layout()
        fig.subplots_adjust(wspace=0.05)
        fig.savefig(output)
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_smoke_{}'.format(team_str)] = relpath

    if update_dire:
        _process_side(s_dire, Team.DIRE)
    if update_radiant:
        _process_side(s_dire, Team.RADIANT)

    return metadata


def do_scans(team: TeamInfo, r_query, metadata: dict,
             update_dire=True, update_radiant=True):
    '''Makes plots for the scan origin points for replays in r_query.
       update_dire and update_radiant control updating specific sides.
    '''
    if not update_dire and not update_radiant:
        return metadata

    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']

    s_dire, s_radiant = get_ptbase_tslice(session, r_query,
                                          team=team, Type=Scan)

    def _plot_scans(query, side: Team):
        data = dataframe_xy_time(query, Scan, session)
        fig, ax = plt.subplots(figsize=(10, 13))
        plot_object_position_scatter(data, ax_in=ax)

        team_str = 'dire' if side == Team.DIRE else 'radiant'
        output = team_path / '{}/scan_summary.png'.format(team_str)
        fig.savefig(output, bbox_inches='tight')
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata['plot_scan_{}'.format(team_str)] = relpath

    if update_dire:
        _plot_scans(s_dire, Team.DIRE)
    if update_radiant:
        _plot_scans(s_radiant, Team.RADIANT)

    return metadata


def do_summary(team: TeamInfo, r_query, metadata: dict):
    '''Plots draft summary, player picks, pick pairs and hero win rates
       for the replays in r_query.'''
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']

    draft_summary_df = draft_summary(session, r_query, team)
    fig, extra = plot_draft_summary(*draft_summary_df)
    output = team_path / 'draft_summary.png'
    fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['plot_draft_summary'] = relpath

    hero_picks_df = player_heroes(session, team)
    fig, extra = plot_player_heroes(hero_picks_df)
    fig.tight_layout(h_pad=3.0)
    output = team_path / 'hero_picks.png'
    fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['plot_hero_picks'] = relpath

    pick_pair_df = pair_rate(session, r_query, team)
    fig, extra = plot_pick_pairs(pick_pair_df)
    output = team_path / 'pick_pairs.png'
    fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['plot_pair_picks'] = relpath

    fig, _, extra = plot_pick_context(draft_summary_df[0], team, r_query)
    output = team_path / 'pick_context.png'
    fig.tight_layout(h_pad=3.0)
    fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['plot_pick_context'] = relpath

    hero_win_rate_df = hero_win_rate(r_query, team)
    fig, _ = plot_hero_winrates(hero_win_rate_df)
    output = team_path / 'hero_win_rate.png'
    fig.tight_layout(h_pad=3.0)
    fig.savefig(output, bbox_inches='tight', dpi=300)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['plot_win_rate'] = relpath

    rune_df = get_rune_control(r_query, team)
    fig, _ = plot_runes(rune_df, team)
    output = team_path / 'rune_control.png'
    fig.tight_layout(h_pad=0)
    fig.savefig(output, bbox_inches='tight', dpi=200)
    relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
    metadata['plot_rune_control'] = relpath



    return metadata


def do_statistics(team: TeamInfo, r_query, metadata: dict):
    win_rate_df = win_rate_table(r_query, team)
    win_rate_df = win_rate_df[['First Rate', 'Second Rate', 'All Rate']]
    win_rate_df = win_rate_df.fillna(0)
    win_rate_df = win_rate_df.round(2)
    metadata['stat_win_rate'] = win_rate_df.to_html()

    return metadata


def process_team(team: TeamInfo, metadata, time: datetime, reprocess=False):
    try:
        r_query = team.get_replays(session).filter(Replay.endTimeUTC >= time)
    except SQLAlchemyError as e:
        print(e)
        print("Failed to retrieve replays for team {}".format(team.name))
        quit()
    new_dire, dire_list, new_radiant, radiant_list = is_updated(r_query, team, metadata)
    if reprocess:
        new_dire = True
        new_radiant = True
    if not new_dire and not new_radiant:
        print("No new updates for {}".format(team.name))

        return

    metadata['replays_dire'] = list(dire_list)
    metadata['replays_radiant'] = list(radiant_list)

    print("Processing drafts.")
    metadata = do_draft(team, metadata, new_dire, new_radiant)
    plt.close('all')
    print("Processing positioning.")
    metadata = do_positioning(team, r_query,
                              -2*60, 10*60,
                              metadata,
                              new_dire, new_radiant
                              )
    plt.close('all')
    print("Processing wards.")
    metadata = do_wards(team, r_query, metadata, new_dire, new_radiant)
    plt.close('all')
    print("Processing smoke.")
    metadata = do_smoke(team, r_query, metadata, new_dire, new_radiant)
    plt.close('all')
    print("Processing scans.")
    metadata = do_scans(team, r_query, metadata, new_dire, new_radiant)
    plt.close('all')
    print("Processing summary.")
    metadata = do_summary(team, r_query, metadata)
    plt.close('all')
    print("Processing statistics.")
    metadata = do_statistics(team, r_query, metadata)

    path = store_metadata(team, metadata)
    print("Metadata file updated at {}".format(str(path)))

    return metadata


def get_team(name):
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == name).one_or_none()

    return team


if __name__ == "__main__":
    args = arguments.parse_args()
    print(args)

    if args.use_time is not None:
        if args.use_time not in ImportantTimes:
            print("--use_time must correspond to a time in ImportantTimes:")
            print(*(k for k in ImportantTimes.keys()))
            exit()
        TIME_CUT = ImportantTimes[args.use_time]

    if args.custom_time is not None:
        TIME_CUT = datetime.utcfromtimestamp(args.custom_time)

    if args.process_teams is not None:
        for proc_team in args.process_teams:
            team = get_team(proc_team)
            if team is None:
                print("Unable to find team {} in database!"
                      .format(proc_team))

            metadata = get_create_metadata(team, args.use_dataset)
            metadata['time_cut'] = TIME_CUT.timestamp()
            process_team(team, metadata, TIME_CUT, args.reprocess)

        exit()

    for team in team_session.query(TeamInfo):
        metadata = get_create_metadata(team, args.use_dataset)
        metadata['time_cut'] = TIME_CUT.timestamp()
        process_team(team, metadata, TIME_CUT, args.reprocess)

