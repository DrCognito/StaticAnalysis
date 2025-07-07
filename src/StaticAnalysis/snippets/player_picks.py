from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from herotools.important_times import MAIN_TIME
from StaticAnalysis.analysis.Player import player_heroes

falcons = get_team(9247354)
r_filter = falcons.filter
df = player_heroes(session, falcons, r_filt=r_filter, limit=None, summarise=False)
