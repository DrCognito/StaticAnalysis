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
from replays.TeamSelections import TeamSelections, PickBans


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
# OG
team_id = 2586976

t_filter = Replay.endTimeUTC >= time

def get_team(name) -> TeamInfo:
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

# Dire example
rq_dire = team.get_replays(session).filter(Replay.replayID == 6505724028)
# Radiant example
rq_radiant = team.get_replays(session).filter(Replay.replayID == 6505843663)

liquid = get_team(2163)
print(liquid.players[0].name)

hero = "npc_dota_hero_puck"
latest5 = [r.replayID for r in r_query.order_by(Replay.replayID.desc()).limit(5)]
pick_filter = and_(or_(TeamSelections.teamID == team.team_id, TeamSelections.stackID == team.stack_id),
                       TeamSelections.draft.any(and_(PickBans.hero == hero, PickBans.is_pick)))

full_filter = and_(TeamSelections.replay_ID.in_(latest5), pick_filter)

t_filter = r_query.limit(5).subquery()
# replays = r_query.join(t_filter, Replay.replayID == t_filter.c.replayID).filter(pick_filter)
replays = r_query.join(TeamSelections, TeamSelections.replay_ID == Replay.replayID).filter(full_filter)

new_cut_time = ImportantTimes['Patch_7_32']
t_filter = (Replay.endTimeUTC >= new_cut_time)
test = session.query(Replay).filter(t_filter).order_by(Replay.replayID)
print(test.first().replayID)
