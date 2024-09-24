from StaticAnalysis.snippets.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.route_vis import plot_pregame_players
import matplotlib.pyplot as plt

replay = session.query(Replay).filter(Replay.replayID == 7957516700).one()
nigma = team_session.query(TeamInfo).filter(TeamInfo.team_id == 7554697).one()
avulus = team_session.query(TeamInfo).filter(TeamInfo.team_id == 9498970).one()

fig = plt.figure(figsize=(7, 7))

plot_pregame_players(replay, nigma, Team.DIRE, session, team_session, fig)
fig.tight_layout()
fig.savefig("wardroute_dire.png")
fig.clf()

plot_pregame_players(replay, avulus, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig("wardroute_radiant.png")
fig.clf()