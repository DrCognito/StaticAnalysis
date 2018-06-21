import Setup
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.Replay import win_rate_table
from analysis.Player import cumulative_player, player_heroes
from replays.Replay import Replay, determine_side_byteam
from replays.Player import Player
from replays.TeamSelections import TeamSelections
from lib.team_info import Teams

s_maker = Setup.get_testDB()
session = s_maker()

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