import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from os import environ as environment
from dotenv import load_dotenv
from lib.team_info import InitTeamDB
from replays.Replay import InitDB, Replay, Team
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from lib.important_times import ImportantTimes
from sqlalchemy import and_, or_
from lib.team_info import InitTeamDB, TeamInfo


load_dotenv(dotenv_path="../setup.env")
DB_PATH = environment['PARSED_DB_PATH']
PLOT_BASE_PATH = environment['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()

time = ImportantTimes['PostTI2021']
replay_list = None
team_id = 2586976

t_filter = Replay.endTimeUTC >= time

def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team
team = get_team(team_id)

r_filter = Replay.endTimeUTC >= time

if replay_list is not None:
    r_filter = and_(Replay.replayID.in_(replay_list), r_filter)
try:
    r_query = team.get_replays(session).filter(r_filter)
except SQLAlchemyError as e:
    print(e)
    print("Failed to retrieve replays for team {}".format(team.name))
    quit()