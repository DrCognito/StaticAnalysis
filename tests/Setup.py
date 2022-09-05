import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from os import environ

from replays.Replay import populate_from_JSON_file, InitDB
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from lib.team_info import InitTeamDB
from dotenv import load_dotenv

engine = InitDB('sqlite:///Data/testing.db')
Session = sessionmaker(bind=engine)
session = Session()

load_dotenv(dotenv_path="test.env")
DB_PATH = environ['PARSED_DB_PATH']
engine_full = InitDB(DB_PATH)
Session_full = sessionmaker(bind=engine_full)


def get_fullDB():
    return Session_full()


def make_testDB(skip_existing=True):
    json_files = list(Path('./tests/Data/').glob('*.json'))
    for j in json_files:
        print(j)
        populate_from_JSON_file(j, session, skip_existing)
    session.commit()

    return Session


def get_team_session():
    team_engine = InitTeamDB()
    team_maker = sessionmaker(bind=team_engine)
    return team_maker()


def reprocess_testDB():
    make_testDB(skip_existing=False)


def get_testDB():
    return Session
