from StaticAnalysis.tests.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.route_vis import plot_pregame_players
import matplotlib.pyplot as plt

replay = session.query(Replay).filter(Replay.replayID == 7117458330).one()
team_alliance = team_session.query(TeamInfo).filter(TeamInfo.team_id == 111474).one()
team_att = team_session.query(TeamInfo).filter(TeamInfo.team_id == 8687717).one()

fig = plt.figure(figsize=(7, 7))

plot_pregame_players(replay, team_alliance, Team.DIRE, session, team_session, fig)
fig.tight_layout()
fig.savefig("test_alliance_dire.png")
fig.clf()

plot_pregame_players(replay, team_att, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig("test_att_radiant.png")
fig.clf()