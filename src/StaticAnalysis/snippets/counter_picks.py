import Setup
import os
import sys
from typing import List
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.Common import get_team
from replays.Replay import Replay, Team
from analysis.Replay import get_ptbase_tslice, get_ptbase_tslice_side, counter_picks
from replays.Ward import Ward, WardType 
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()
load_dotenv(dotenv_path="../setup.env")

# teamName = "Royal Never Give Up"
teamName = "Hippomaniacs"
team = get_team(team_session, teamName)
# Royal never give up test case for bad pos
# r_query = team.get_replays(session).filter(Replay.replayID == 4857623860)
r_query = team.get_replays(session)
# r_query = r_query.limit(20)


test = counter_picks(session, r_query, team)
# Remove 0 columns (unpicked heroes)
test = test.T[test.any()].T
# Get a series without 0s
grimstroke = test['Grimstroke'].loc[lambda x: x != 0]
# Plot
grimstroke.plot.bar()