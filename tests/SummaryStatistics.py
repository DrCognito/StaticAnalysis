import Setup
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.Replay import win_rate_table
from analysis.Player import cumulative_player, player_heroes, pick_context
from analysis.Replay import hero_win_rate, get_ptbase_tslice, pair_rate
from replays.Replay import Replay, determine_side_byteam
from replays.Player import Player
from replays.TeamSelections import TeamSelections
from replays.Ward import Ward, WardType
from replays.Rune import Rune, RuneID
from replays.Scan import Scan
from lib.team_info import InitTeamDB, TeamInfo
from sqlalchemy.orm import sessionmaker

s_maker = Setup.get_testDB()
session = s_maker()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()

Teams = {
    'Mad Lads': team_session.query(TeamInfo)
                            .filter(TeamInfo.team_id == 5229049).one()
}

team_test_id = 5229049
#team_test_id = 1375614

filt = (Replay.teams.any(TeamSelections.teamID == team_test_id), )

test = win_rate_table(session, Teams['Mad Lads'])
print(test)

#Synderen
p_filter = (Player.steamID == 76561198047004422)
test_p = cumulative_player(session, 'last_hits', Teams['Mad Lads'], p_filter)
print(test_p.resample('10T').sum())

test_picks = player_heroes(session, Teams['Mad Lads'], summarise=10)
print(test_picks)

r_query = Teams['Mad Lads'].get_replays(session)
test_context = pick_context('npc_dota_hero_beastmaster', Teams['Mad Lads'],
                            r_query)

test_hero_pick = hero_win_rate(r_query, Teams['Mad Lads'])
test_wards = get_ptbase_tslice(session, r_query, team=Teams['Mad Lads'],
                                Type=Ward,
                                start=-2*60, end=10*60)
test_scans = get_ptbase_tslice(session, r_query, team=Teams['Mad Lads'],
                                Type=Scan,
                                start=-2*60, end=10*60)
test_runes = get_ptbase_tslice(session, r_query, team=Teams['Mad Lads'],
                                Type=Rune,
                                start=-2*60, end=10*60)

test_pairs = pair_rate(session, r_query, Teams['Mad Lads'])