import Setup
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.Replay import win_rate_table
from replays.Replay import Replay, determine_side_byteam
from replays.TeamSelections import TeamSelections

s_maker = Setup.get_testDB()
session = s_maker()

team_test_id = 5229049
#team_test_id = 1375614

filt = (Replay.teams.any(TeamSelections.teamID == team_test_id), )

test = win_rate_table(session, filt,
                      lambda x: determine_side_byteam(team_test_id, x))
