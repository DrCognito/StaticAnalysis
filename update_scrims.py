from ast import Str
import pathlib
from dotenv import load_dotenv
from os import environ as environment
from lib.team_info import InitTeamDB, TeamInfo
from sqlalchemy.orm import sessionmaker
import pygsheets
import json

load_dotenv(dotenv_path="setup.env")
SCRIMS_JSON_PATH = environment['SCRIMS_JSON']
TEAMS_JSON_PATH = environment['SCRIMS_TEAMS']
main_team_id = 2586976
main_team_name = "OG"

with open(TEAMS_JSON_PATH, 'r') as f:
    team_map = json.load(f)

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()
unknown_teams = set()


def get_team_id(name: Str) -> int:
    if name in team_map:
        name = team_map[name]
    team: TeamInfo = team_session.query(TeamInfo).filter(TeamInfo.name == name).one_or_none()
    if team is None:
        unknown_teams.add(name)
        return None
    else:
        return team.team_id

gc = pygsheets.authorize(outh_file="client_secret_1032893103395-vtiha2lmocsru6nvc96ipnrjj10lue23.apps.googleusercontent.com.json")
sheet = gc.open_by_key('1HbH7GShRz7-kuVVlMaehmSm_AXBSCvGwmYuDYvLfhpA')

scrim_sheet = sheet.worksheet_by_title(r"Past Scrim ID's")
# Column uses numbers, starting at 1! returns list[string]
team_names = scrim_sheet.get_col(2)
scrim_ids = scrim_sheet.get_col(3)

if len(team_names) != len(scrim_ids):
    print("Warning: team names do not match scrim ids in length!")
scrim_dict = {}

for scrim_id, name in zip(scrim_ids[2:], team_names[2:]):
    if scrim_id == '':
        # Lots of trailing info in the columns.
        continue
    if len(scrim_id) != 10:
        print(f"Skipping unusual scrim ID {scrim_id}")
        continue
    # Default to the string if its wrong
    name = name.strip()
    team_id = get_team_id(name)
    team_id = team_id if team_id is not None else name

    if team_id in scrim_dict:
        scrim_dict[team_id][int(scrim_id)] = main_team_name
    else:
        scrim_dict[team_id] = {int(scrim_id): main_team_name}
    # Do OG also
    if main_team_id in scrim_dict:
        scrim_dict[main_team_id][int(scrim_id)] = name
    else:
        scrim_dict[main_team_id] = {int(scrim_id): name}


with open(SCRIMS_JSON_PATH, 'w') as f:
    json.dump(scrim_dict, f)


if len(unknown_teams) != 0:
    print("None matched teams: ")
    print(', '.join(unknown_teams))
