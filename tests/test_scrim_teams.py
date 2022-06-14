from typing import Set
import minimal_db as db
import pathlib
from dotenv import load_dotenv
from os import environ as environment
from lib.team_info import InitTeamDB, TeamInfo
from sqlalchemy.orm import sessionmaker
import pygsheets
import json
from replays.Replay import InitDB, Replay, Team
from replays.TeamSelections import TeamSelections

load_dotenv(dotenv_path="setup.env")
SCRIMS_JSON_PATH = environment['SCRIMS_JSON']
TEAMS_JSON_PATH = environment['SCRIMS_TEAMS']
main_team_id = 2586976
main_team_name = "OG"
main_team: TeamInfo = db.get_team(main_team_id)
main_players = {x.player_id for x in main_team.players}

with open(TEAMS_JSON_PATH, 'r') as f:
    team_map = json.load(f)

with open(SCRIMS_JSON_PATH, 'r') as f:
    scrims = json.load(f)

scrim_ids = [x for y in scrims for x in scrims[y]]

replays = db.session.query(Replay).filter(Replay.replayID.in_(scrim_ids))


def is_player_match(players_a: Set, players_b: Set, overlap: int):
    if len(players_a) != len(players_b):
        print(f"{players_a} | {players_b}")
        raise ValueError
    if len(players_a) < overlap:
        print(f"{players_a} | {players_b}")
        raise ValueError

    tot_players = len(players_a)
    remaining = players_a - players_b

    return len(remaining) <= (tot_players - overlap)


def test_replays(r: Replay):
    valid = True
    found_mt = False
    t: TeamSelections
    for t in r.teams:
        if t.teamName == '':
            print(f"Invalid teamName {r.replayID}")
            valid = False
        elif t.teamName == main_team_name:
            found_mt = True

        if t.teamID == 0:
            print(f"Invalid teamID {r.replayID}")
            valid = False
        elif t.teamID == main_team_id:
            found_mt = True
            player_set = {x.steamID for x in r.get_players(t.team)}
            if not is_player_match(player_set, main_players, 4):
                print(f"Mainteam could not be matched with main team players.")
    if not found_mt:
        print(f"Could not find main team in {r.replayID}! {main_team_name},: {main_team_id}")

    return valid and found_mt

good = 0
bad = 0
for r in replays:
    success = test_replays(r)
    if success:
        good += 1
    else:
        bad += 1

print(f"Good: {good}, Bad: {bad}")


