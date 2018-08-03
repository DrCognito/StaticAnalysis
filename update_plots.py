import json
from argparse import ArgumentParser
from datetime import datetime
from os import environ as environment
from os import mkdir
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from analysis.Player import (cumulative_player, pick_context, player_heroes,
                             player_position)
from analysis.Replay import (draft_summary, get_ptbase_tslice, get_smoke,
                             hero_win_rate, pair_rate, win_rate_table)
from analysis.visualisation import (dataframe_xy, dataframe_xy_time,
                                    dataframe_xy_time_smoke,
                                    plot_draft_summary, plot_hero_winrates,
                                    plot_map_points, plot_object_position,
                                    plot_object_position_scatter,
                                    plot_pick_context, plot_pick_pairs,
                                    plot_player_heroes,
                                    plot_player_positioning)
from analysis.draft_vis import replay_draft_image
from lib.Common import (dire_ancient_cords, location_filter,
                        radiant_ancient_cords)
from lib.important_times import ImportantTimes
from lib.metadata import is_updated, make_meta
from lib.team_info import TeamInfo
from replays.Player import Player, PlayerStatus
from replays.Replay import InitDB, Replay, Team
from replays.Ward import Ward, WardType
from replays.TeamSelections import TeamSelections

load_dotenv(dotenv_path="setup.env")
DB_PATH = environment['PARSED_DB_PATH']
PLOT_BASE_PATH = environment['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

TIME_CUT = ImportantTimes['2018']

arguments = ArgumentParser()
arguments.add_argument('--process_team',
                       help='''Process specific team.''')
arguments.add_argument('--using_leagues',
                       help='''Use replays only from these league ids.''',
                       nargs='*')
arguments.add_argument('--use_dataset',
                       help='''Use this or create a new dataset
                               for these options.''')
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
    team_path = Path(PLOT_BASE_PATH) / TeamInfo.name
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


def do_positioning(team: TeamInfo, r_query,
                   start: int, end: int,
                   metadata: dict,
                   update_dire=True, update_radiant=True,
                   positions=(0, 1, 2, 3, 4)):
    '''Make the positioning plots between start and end times for
       positions in r_query.
       update_dire and update_radiant control updating specific side.
       NOTE: Positions are zero based!
       Returns true if plots have been made and metadata updated.
    '''
    if not update_dire and not update_radiant:
        return metadata

    team_path = Path(PLOT_BASE_PATH) / TeamInfo.name / metadata.name
    for pos in positions:
        pos_dire, pos_radiant = player_position(session, r_query, team,
                                                player_slot=pos,
                                                start=start, end=end)

        if update_dire:
            output = team_path / 'dire' / (team.players[pos] + '.png')
            dire_ancient_filter = location_filter(dire_ancient_cords,
                                                  PlayerStatus)
            pos_dire = pos_dire.filter(dire_ancient_filter)
            fig, ax = plot_player_positioning(dataframe_xy(pos_dire,
                                                           PlayerStatus,
                                                           session))
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            metadata['plot_p{}pos_dire'.format(str(pos))] = \
                str(output)

        if update_radiant:
            output = team_path / 'radiant' / (team.players[pos] + '.png')
            ancient_filter = location_filter(radiant_ancient_cords,
                                             PlayerStatus)
            pos_radiant = pos_radiant.filter(ancient_filter)
            fig, ax = plot_player_positioning(dataframe_xy(pos_radiant,
                                                           PlayerStatus,
                                                           session))
            fig.tight_layout()
            fig.savefig(output, bbox_inches='tight')
            metadata['plot_p{}pos_radiant'.format(str(pos))] = \
                str(output)

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
    team_path = Path(PLOT_BASE_PATH) / TeamInfo.name / metadata.name

    if update_dire:
        output = team_path / 'dire/drafts.png'
        dire_drafts = replay_draft_image(r_drafted.filter(dire_filter).all(),
                                         Team.DIRE,
                                         team.name)
        dire_drafts.save(output)
        metadata['plot_dire_drafts'] = str(output)

    if update_radiant:
        output = team_path / 'radiant/drafts.png'
        radiant_drafts = replay_draft_image(r_drafted.filter(radiant_filter).all(),
                                            Team.RADIANT,
                                            team.name)
        radiant_drafts.save(output)
        metadata['plot_radiant_drafts'] = str(output)

    return metadata


def do_wards(team: TeamInfo, r_query,
             metadata: dict,
             update_dire=True, update_radiant=True):

    if not update_dire and not update_radiant:
        return metadata
    team_path = Path(PLOT_BASE_PATH) / TeamInfo.name / metadata.name

    wards_dire, wards_radiant = get_ptbase_tslice(session, r_query, team,
                                                  Ward,
                                                  start=-2*60, end=10*60)
    wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
    wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)

    if update_dire:
        output = team_path / 'dire'
        ward_df = dataframe_xy_time(wards_dire, Ward, session)

        fig, _ = plot_object_position(ward_df.loc[ward_df['game_time'] <= 0])
        fig.tight_layout()
        fig.savefig(output / 'wards_pregame.png')
        metadata['plot_ward_t1_dire'] = str(output / 'wards_pregame.png')

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 0) and
                                                  (ward_df['game_time'] <= 4*60)])
        fig.tight_layout()
        fig.savefig(output / 'wards_0to4.png')
        metadata['plot_ward_t2_dire'] = str(output / 'wards_0to4.png')

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 4*60) and
                                                  (ward_df['game_time'] <= 8*60)])
        fig.tight_layout()
        fig.savefig(output / 'wards_4to8.png')
        metadata['plot_ward_t3_dire'] = str(output / 'wards_4to8.png')

    if update_radiant:
        output = team_path / 'radiant'
        ward_df = dataframe_xy_time(wards_radiant, Ward, session)

        fig, _ = plot_object_position(ward_df.loc[ward_df['game_time'] <= 0])
        fig.tight_layout()
        fig.savefig(output / 'wards_pregame.png')
        metadata['plot_ward_t1_radiant'] = str(output / 'wards_pregame.png')

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 0) and
                                                  (ward_df['game_time'] <= 4*60)])
        fig.tight_layout()
        fig.savefig(output / 'wards_0to4.png')
        metadata['plot_ward_t2_radiant'] = str(output / 'wards_0to4.png')

        fig, _ = plot_object_position(ward_df.loc[(ward_df['game_time'] > 4*60) and
                                                  (ward_df['game_time'] <= 8*60)])
        fig.tight_layout()
        fig.savefig(output / 'wards_4to8.png')
        metadata['plot_ward_t3_radiant'] = str(output / 'wards_4to8.png')

    return metadata


def process_team(team: TeamInfo, metadata):
    try:
        r_query = team.get_replays(session)
    except SQLAlchemyError as e:
        print(e)
        print("Failed to retrieve replays for team {}".format(team.name))
        quit()
    new_dire, new_radiant = is_updated(r_query, team, metadata)
    if not new_dire and not new_radiant:
        print("No new updates for {}".format(team.name))

    metadata = do_draft(team, metadata, new_dire, new_radiant)
    metadata = do_positioning(team, r_query,
                              -2*60, 10*60,
                              metadata,
                              new_dire, new_radiant
                              )
    metadata = do_wards(team, r_query, new_dire, new_radiant)


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
