from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from propubs.model.pub_heroes import InitDB as InitPubDB
from StaticAnalysis.lib.team_info import InitTeamDB, TeamInfo
from StaticAnalysis.replays.Replay import InitDB, Replay, Team
from os import environ as environment

load_dotenv(dotenv_path="../../setup.env")
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
