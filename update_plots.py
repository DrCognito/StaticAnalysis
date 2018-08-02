from argparse import ArgumentParser
from os import environ as environment
from os import mkdir
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from lib.metadata import make_meta
from lib.team_info import TeamInfo
from lib.important_times import ImportantTimes
from replays.Replay import InitDB, populate_from_JSON_file
import json

load_dotenv(dotenv_path="setup.env")
DB_PATH = environment['PARSED_DB_PATH']
PLOT_BASE_PATH = environment['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()


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
    
    meta_json = team_path / 'meta_data.json'
    if meta_json.exists():
        with open(meta_json, 'r') as file:
            json_file = json.load(file)
        if dataset in json_file:
            return json_file[dataset]

    return make_meta(dataset)


if __name__ == "__main__":
    args = arguments.parse_args()
    print(args)

    if args.use_time is not None:
        if args.use_time not in ImportantTimes:
            print("--use_time must correspond to a time in ImportantTimes:")
            print(*(k for k in ImportantTimes.keys()))
            exit()