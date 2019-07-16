import Setup
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Ward import Ward, WardType
from replays.Replay import Replay
from replays.Player import Player
from replays.Smoke import Smoke
from lib.team_info import InitTeamDB, TeamInfo, TeamPlayer
from analysis.Replay import get_ptbase_tslice
from pandas import DataFrame, read_sql

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()


def get_team(name):
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == name).one_or_none()

    return team


def get_player(steam_id):
    player = team_session.query(TeamPlayer.player_id == steam_id).one_or_none

    if player is None:
        raise ValueError
    else:
        return player


# Dire 4901517396
# Radiant 4901403209
team = get_team("Royal Never Give Up")
r_query = team.get_replays(session).filter(Replay.replayID == 4857623860)
#d_query = team.get_replays(session).filter(Replay.replayID == 4901517396)
_, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                              Type=Ward,
                                              start=-2*60, end=20*60)
# wards_dire, _ = get_ptbase_tslice(session, d_query, team=team,
#                                               Type=Ward,
#                                               start=-2*60, end=20*60)
# wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)


sql_query = wards_radiant.with_entities(Ward.xCoordinate,
                Ward.yCoordinate,
                Ward.steamID,
                Ward.game_time,
                Ward.from_smoke).statement

data = read_sql(sql_query, session.bind)
# def build_table(wards):

#     for w in wards:

smokes = session.query(Smoke).filter(Smoke.replayID == 4903243468)
tp = smokes[1].players_smoked
sigh = [x.steam_id for x in tp] 