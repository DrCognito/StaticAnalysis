from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from herotools.important_times import MAIN_TIME
from StaticAnalysis.analysis.Player import player_heroes
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TeamSelections import TeamSelections, PickBans
from herotools.HeroTools import convertName, HeroIDType, HeroIconPrefix
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image
from scipy.stats import binomtest
from pathlib import Path
from StaticAnalysis.analysis.picks import do_loss_opp_picks

falcons = get_team(9247354)
r_filter = falcons.filter
# df = player_heroes(session, falcons, r_filt=r_filter, limit=None, summarise=False)

r_query = session.query(Replay).filter(falcons.filter).filter(Replay.endTimeUTC > MAIN_TIME)


fig = do_loss_opp_picks(r_query, falcons)
fig.savefig("falcons_loss.png")