from typing import Set
import minimal_db as db
from dotenv import load_dotenv
from os import environ as environment
from lib.team_info import InitTeamDB, TeamInfo
from sqlalchemy.orm import sessionmaker
import json
from replays.Replay import InitDB, Replay, Team
from replays.TeamSelections import TeamSelections

load_dotenv(dotenv_path="test.env")
SCRIMS_JSON_PATH = environment['SCRIMS_JSON']
TEAMS_JSON_PATH = environment['SCRIMS_TEAMS']
main_team_id = 2586976
main_team_name = "OG"
main_team: TeamInfo = db.get_team(main_team_id)
main_players = {x.player_id for x in main_team.players}

MIN_MATCH_MEMBERS = 3

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


def test_replay(r: Replay, min_members):
    valid = True
    found_mt = False
    t: TeamSelections
    for t in r.teams:
        if t.teamName == '':
            # print(f"Invalid teamName {r.replayID}")
            valid = False
        elif t.teamName == main_team_name:
            found_mt = True

        if t.teamID == 0:
            # print(f"Invalid teamID {r.replayID}")
            valid = False
        elif t.teamID == main_team_id:
            found_mt = True
            player_set = {x.steamID for x in r.get_players(t.team)}
            if not is_player_match(player_set, main_players, min_members):
                print(f"Mainteam could not be matched with main team players.")
    if not found_mt:
        print(f"Could not find main team in {r.replayID}! {main_team_name},: {main_team_id}")

    return valid and found_mt

good = 0
bad = 0
for r in replays:
    success = test_replay(r, MIN_MATCH_MEMBERS)
    if success:
        good += 1
    else:
        bad += 1

print(f"Good: {good}, Bad: {bad}")


def assign_team(main_team: TeamInfo, other_team: TeamInfo, replay: Replay, min_members=3):
    for t in replay.teams:
        if t.team == Team.DIRE:
            dire_team: TeamSelections = t
        else:
            radiant_team: TeamSelections = t

    dire_main = main_team.team_id == dire_team.teamID
    radiant_main = main_team.team_id == radiant_team.teamID
    assert(not(dire_main and radiant_main))

    if dire_main:
        radiant_team.teamID = other_team.team_id
        print("Assigned opposition to radiant from existing main ID.")

    if radiant_main:
        dire_team.teamID = other_team.team_id
        print("Assigned opposition to dire from existing main ID.")

    dire_players = {x.steamID for x in replay.get_players(Team.DIRE)}
    radiant_players = {x.steamID for x in replay.get_players(Team.RADIANT)}

    main_players = {x.player_id for x in main_team.players}
    main_dire = is_player_match(main_players, dire_players, min_members)
    main_radiant = is_player_match(main_players, radiant_players, min_members)

    other_players = {x.player_id for x in other_team.players}
    try:
        other_dire = is_player_match(other_players, dire_players, min_members)
        other_radiant = is_player_match(other_players, radiant_players, min_members)
    except ValueError as e:
        print(f"Team {other_team.team_id}, {other_team.name}, incorrect player numbers.")
        raise e

    # Can not have a team match both teams
    assert(not(main_dire and main_radiant))
    assert(not(other_radiant and other_dire))

    # Can not have teams match the same team
    assert(not(main_dire and other_dire))
    assert(not(main_radiant and other_radiant))

    if main_dire:
        dire_team.teamID = main_team.team_id
        dire_team.teamName = main_team.name
    elif main_radiant:
        radiant_team.teamID = main_team.team_id
        radiant_team.teamName = main_team.name

    if other_dire:
        print(f"Dire should be {other_team.team_id}")
        dire_team.teamID = other_team.team_id
        dire_team.teamName = other_team.name
    elif other_radiant:
        print(f"Radiant should be {other_team.team_id}")
        radiant_team.teamID = other_team.team_id
        radiant_team.teamName = other_team.name

    # We found a main team but not the opposition at all, we can just go round
    # if (main_dire or main_radiant) and not (other_dire or other_radiant):
    #     assign_team(main_team, other_team, replay, min_members)

    # db.session.add(dire_team)
    # db.session.add(radiant_team)
    db.session.commit()


for t in scrims:
    other_team = db.get_team(t)
    if other_team is None:
        print(f"Could not find team {t}")
        continue
    if other_team.name == main_team.name:
        continue

    for r_id in scrims[t]:
        replay = db.session.query(Replay).filter(Replay.replayID == r_id).one_or_none()
        if replay is None:
            print(f"Replay {r_id} not found.")
            continue
        if not test_replay(replay, MIN_MATCH_MEMBERS):
            print(f"Attempting to fix {replay.replayID}")
            try:
                assign_team(main_team, other_team, replay, MIN_MATCH_MEMBERS)
            except ValueError:
                continue