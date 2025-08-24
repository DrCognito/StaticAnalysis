from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TwinGate import TwinGate
from herotools.important_times import MAIN_TIME
from pandas import DataFrame, IntervalIndex, cut
import matplotlib.pyplot as plt
import seaborn as sns
from StaticAnalysis.lib.Common import seconds_to_nice
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.Player import Player
from itertools import chain
from StaticAnalysis.vis.twin_gate import get_dataframe_counts

falcons = get_team(9247354)
falcons.get_replays(session, Replay.endTimeUTC >= MAIN_TIME)