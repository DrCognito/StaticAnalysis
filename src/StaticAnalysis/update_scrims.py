import json
import pathlib

import pygsheets
from herotools.important_times import ImportantTimes, MAIN_TIME
from sqlalchemy.orm import sessionmaker

import StaticAnalysis
from StaticAnalysis import session, team_session
from StaticAnalysis.lib.team_info import InitTeamDB, TeamInfo
from StaticAnalysis.lib.team_info import get_team as id_to_team
from StaticAnalysis.replays.Replay import InitDB, Replay, Team
# Log setup
from loguru import logger as LOG
from tqdm import tqdm
LOG.remove()
LOG.add(lambda msg: tqdm.write(msg, end=""), format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> <level>{level}</level> {message}", colorize=True, level='INFO')
LOG.add("scrims.log", rotation="5 MB", level='DEBUG', retention=0)


SCRIMS_JSON_PATH = StaticAnalysis.CONFIG['scrims']['SCRIMS_JSON']
TEAMS_JSON_PATH = StaticAnalysis.CONFIG['scrims']['SCRIMS_TEAMS']
SCRIMS_METAJSON_PATH = StaticAnalysis.CONFIG['scrims']['SCRIMS_META']

main_team_id = StaticAnalysis.CONFIG['team']['TEAM_ID']
main_team_name = StaticAnalysis.CONFIG['team']['TEAM_NAME']
time_cut = MAIN_TIME

with open(TEAMS_JSON_PATH, 'r') as f:
    team_map = json.load(f)

meta_path = pathlib.Path(SCRIMS_METAJSON_PATH)

missing_teams = set()
unfixed_replays = set()
fixed_replays = set()
replays = set()
missing = set()

unknown_teams = set()


def get_team(name: str | int) -> TeamInfo:
    if name in team_map:
        name = team_map[name]
    team: TeamInfo = team_session.query(TeamInfo).filter(TeamInfo.name == name).one_or_none()
    if team is None:
        unknown_teams.add(name)
        return None

    return team


def get_team_id(name: str) -> int:
    team = get_team(name)

    if team is not None:
        return team.team_id

    return None


def is_valid_replay(replay: Replay) -> bool:
    if len(replay.teams) != 2:
        LOG.debug(f"Warning invalid number of teams in {replay.replayID}.")
        return False
    if replay.teams[0].teamID == 0:
        LOG.debug(f"{replay.replayID}: teams[0].teamID is 0!")
        return False
    if replay.teams[0].teamName == '':
        LOG.debug(f"{replay.replayID}: teams[0].teamName is ''")
        return False
    if replay.teams[1].teamID == 0:
        LOG.debug(f"{replay.replayID}: teams[1].teamID is 0!")
        return False
    if replay.teams[1].teamName == '':
        LOG.debug(f"{replay.replayID}: teams[1].teamName is ''")
        return False
    if replay.teams[0].teamID == replay.teams[1].teamID:
        LOG.debug(f"{replay.replayID}: Found duplicate team for {replay.replayID}.")
        return False
    if replay.teams[0].teamName == replay.teams[1].teamName:
        LOG.debug(f"{replay.replayID}: Found duplicate team for {replay.replayID}.")
        return False
    if replay.teams[0].teamID != main_team_id and replay.teams[1].teamID != main_team_id:
        LOG.debug(f"{replay.replayID}: Main team is missing.")
        return False

    return True


def fix_replay_mainonly(replay: Replay) -> Replay:
    player_min = 2
    main_side = replay.get_side(main_team)
    team_dict = replay.get_team_dict()
    if main_side is not None:
        LOG.warning(f"Main team already asigned for {replay.replayID}!")
        team_dict[main_side].teamID = main_team.team_id
        team_dict[main_side].teamName = main_team.name
        return replay
    main_players = {p.player_id for p in main_team.players}
    n_dire = replay.matching_players(main_players, Team.DIRE)
    n_radiant = replay.matching_players(main_players, Team.RADIANT)

    if n_dire > n_radiant and n_dire >= player_min:
        team_dict[Team.DIRE].teamID = main_team.team_id
        team_dict[Team.DIRE].teamName = main_team.name
    elif n_radiant > n_dire and n_radiant >= player_min:
        team_dict[Team.RADIANT].teamID = main_team.team_id
        team_dict[Team.RADIANT].teamName = main_team.name

    assert(team_dict[Team.DIRE].teamID != team_dict[Team.RADIANT].teamID)

    return replay


def fix_replay(replay: Replay, opposition: TeamInfo, n_pmatch=3) -> bool:
    """"Attempt to correct the team info for a replay."""

    def _asign(main_s: Team, opp_s: Team):
        team_dict[main_s].teamID = main_team.team_id
        team_dict[main_s].teamName = main_team.name

        team_dict[opp_s].teamID = opposition.team_id
        team_dict[opp_s].teamName = opposition.name

    team_dict = replay.get_team_dict()
    main_side = replay.get_side(main_team)
    if main_side is not None:
        opp_side = Team.DIRE if main_side == Team.RADIANT else Team.RADIANT
        _asign(main_s=main_side, opp_s=opp_side)
        return True

    opp_side = replay.get_side(opposition)
    if opp_side is not None:
        main_side = Team.DIRE if opp_side == Team.RADIANT else Team.RADIANT
        _asign(main_s=main_side, opp_s=opp_side)
        return True

    main_players = {p.player_id for p in main_team.players}
    main_dire = replay.matching_players(main_players, Team.DIRE) >= n_pmatch
    main_radiant = replay.matching_players(main_players, Team.RADIANT) >= n_pmatch
    assert(not(main_dire and main_radiant))
    if main_dire:
        _asign(Team.DIRE, Team.RADIANT)
        return True
    if main_radiant:
        _asign(Team.RADIANT, Team.DIRE)
        return True

    opp_players = {p.player_id for p in opposition.players}
    opp_dire = replay.matching_players(opp_players, Team.DIRE) >= n_pmatch
    opp_radiant = replay.matching_players(opp_players, Team.RADIANT) >= n_pmatch
    assert(not(opp_dire and opp_radiant))
    if opp_dire:
        _asign(Team.RADIANT, Team.DIRE)
        return True
    if opp_radiant:
        _asign(Team.DIRE, Team.RADIANT)
        return True

    return False


def get_matching_main(replay: Replay, opposition: TeamInfo):
    main_players = {p.player_id for p in main_team.players}
    main_dire = replay.matching_players(main_players, Team.DIRE)
    main_radiant = replay.matching_players(main_players, Team.RADIANT)

    opp_players = {p.player_id for p in opposition.players}
    opp_dire = replay.matching_players(opp_players, Team.DIRE)
    opp_radiant = replay.matching_players(opp_players, Team.RADIANT)

    return {'main_dire': main_dire, 'main_radiant': main_radiant, 
            'opp_dire': opp_dire, 'opp_radiant': opp_radiant}


main_team = get_team(main_team_name)
gc = pygsheets.authorize(outh_file="apps.googleusercontent.com.json")
SCRIMS_SHEETKEY = StaticAnalysis.CONFIG['scrims']['SCRIMS_GOOGLE_SHEET']
sheet = gc.open_by_key(SCRIMS_SHEETKEY)

scrim_sheet = sheet.worksheet_by_title(r"Past Scrim ID's")
# Column uses numbers, starting at 1! returns list[string]
team_names = scrim_sheet.get_col(2)
scrim_ids = scrim_sheet.get_col(3)

if len(team_names) != len(scrim_ids):
    LOG.warning("Sheet column for team names do not match scrim ids in length!")
scrim_dict = {}

for scrim_id, name in tqdm(zip(scrim_ids[2:], team_names[2:]), desc="Sheet"):
    if scrim_id == '':
        # Lots of trailing info in the columns.
        continue
    if len(scrim_id) != 10:
        LOG.warning(f"Skipping unusual scrim ID: '{scrim_id}'")
        continue
    # Default to the string if its wrong
    name = name.strip()
    team_id = get_team_id(name)

    propper_team = True
    if team_id is None:
        team_id = name
        propper_team = False
        missing_teams.add(name)
    # team_id = team_id if team_id is not None else name

    if team_id in scrim_dict:
        scrim_dict[team_id][int(scrim_id)] = main_team_name
    else:
        scrim_dict[team_id] = {int(scrim_id): main_team_name}
    # Do Main also
    if main_team_id in scrim_dict:
        scrim_dict[main_team_id][int(scrim_id)] = name
    else:
        scrim_dict[main_team_id] = {int(scrim_id): name}
    # Validate and fix replays
    replays.add(scrim_id)
    replay: Replay = session.query(Replay).filter(Replay.replayID == scrim_id).one_or_none()
    # Check replay is new enough
    # No replay found
    if replay is None:
        missing.add(scrim_id)
        continue
    if replay.endTimeUTC < time_cut:
        continue
    if is_valid_replay(replay):
        continue

    # Not much we can do if we dont have a propper team to use
    if not propper_team:
        LOG.info(f"Could not fix {scrim_id} (no propper team: {name})")
        unfixed_replays.add(scrim_id)
        continue

    opposition_team = get_team(name)
    fixed = fix_replay(replay, opposition_team)
    fixed = is_valid_replay(replay) and fixed

    if fixed:
        session.commit()
        fixed_replays.add(scrim_id)
        LOG.info(f"Fixed {scrim_id}")
    else:
        res_dict = get_matching_main(replay, opposition_team)
        LOG.info(
            f"Could not fix {scrim_id}, Main (d|r): {res_dict['main_dire']}|{res_dict['main_radiant']},{opposition_team.name} (d|r):{res_dict['opp_dire']}|{res_dict['opp_radiant']}")
        LOG.info(f"Validity: {is_valid_replay(replay)}")
        unfixed_replays.add(scrim_id)

# Get scrims that are downloaded but not in the sheet
from pathlib import Path
scrim_path = Path('E:\\Dota2\\dbScrim\\')
scrim_files = list(scrim_path.glob("*.dem"))
file_ids = {s.stem for s in scrim_files}
# Check the ones we have that are new as above
for scrim_id in tqdm(file_ids.difference(scrim_ids[2:]), desc="DIR only"):
    if not scrim_id.isnumeric():
        LOG.info(f"Invalid scrim id from file {scrim_id}")
        continue
    LOG.debug(f"Checking id {scrim_id} not present in sheet!")

    replay: Replay = session.query(Replay).filter(Replay.replayID == scrim_id).one_or_none()
    if replay is None:
        LOG.debug(f"Missing {scrim_id} in processed db.")
        continue
    # Check to see if it has a league id, probably an official
    if replay.league_ID is None:
        LOG.warning(f"League ID for {scrim_id} is None, skipping.")
        continue
    if replay.league_ID != 0:
        LOG.info(f"League ID for {scrim_id} is not 0, probably an official - skipping.")
        continue
    name = "unknown"
    for t in replay.teams:
        if t.teamID is None or t.teamID == main_team_id:
            continue
        ot = id_to_team(t.teamID)
        if ot is None:
            continue
        name = ot.name
        if ot.team_id in scrim_dict:
            scrim_dict[ot.team_id][int(scrim_id)] = main_team_name
        else:
            scrim_dict[ot.team_id] = {int(scrim_id): main_team_name}
    # Do OG also
    if main_team_id in scrim_dict:
        scrim_dict[main_team_id][int(scrim_id)] = name
    else:
        scrim_dict[main_team_id] = {int(scrim_id): name}

    if is_valid_replay(replay):
        continue

    replay = fix_replay_mainonly(replay)
    session.commit()

    # replay: Replay = session.query(Replay).filter(Replay.replayID == scrim_id).one_or_none()
    # # Check replay is new enough
    # # No replay found
    # if replay is None:
    #     missing.add(scrim_id)
    #     continue
    # if replay.endTimeUTC < time_cut:
    #     continue
    # if is_valid_replay(replay):
    #     continue

with open(SCRIMS_JSON_PATH, 'w') as f:
    json.dump(scrim_dict, f)


if meta_path.exists():
    with open(meta_path, 'r') as f:
        meta_json = json.load(f)
else:
    meta_json = {}
seen_missing_teams = set(meta_json.get("missing_teams", set()))
seen_unfixed_replays = set(meta_json.get("bad_replays", set()))
seen_fixed_replays = set(meta_json.get("fixed_replays", set()))
seen_replays = set(meta_json.get("seen_replays", set()))
seen_missing = set(meta_json.get("seen_missing", set()))

missing_teams_diff = missing_teams - seen_missing_teams
if missing_teams_diff:
    LOG.info(f"New missing teams: {', '.join(missing_teams_diff)}")
    meta_json["missing_teams"] = list(seen_missing_teams | missing_teams_diff)


fixed_diff = fixed_replays - seen_fixed_replays
if fixed_diff:
    LOG.info(f"New fixed replays: {', '.join(fixed_diff)}")
    meta_json["fixed_replays"] = list(seen_unfixed_replays | fixed_diff)


unfixed_diff = unfixed_replays - seen_unfixed_replays
if unfixed_diff:
    LOG.info(f"New unfixable replays: {', '.join(unfixed_diff)}")
    meta_json["bad_replays"] = list(seen_unfixed_replays | unfixed_diff)

missing_diff = missing - seen_missing
if missing_diff:
    LOG.info(f"New missing replays: {', '.join(missing_diff)}")
    meta_json["seen_missing"] = list(seen_missing | missing_diff)


meta_json["seen_replays"] = list(seen_replays | replays)

with open(meta_path, 'w') as f:
    json.dump(meta_json, f)
