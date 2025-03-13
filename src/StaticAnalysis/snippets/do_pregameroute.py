from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.update_plots import get_team
from StaticAnalysis.analysis.Replay import get_side_replays
from StaticAnalysis.analysis.route_vis import plot_pregame_players
import matplotlib.pyplot as plt
from herotools.important_times import MAIN_TIME
from StaticAnalysis import session, team_session

r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = session.query(Replay).filter(r_filter)
team: TeamInfo = get_team(8599101)
d_replays, r_replays = get_side_replays(r_query, session, team)
d_replays = d_replays.order_by(Replay.replayID.desc())
r_replays = r_replays.order_by(Replay.replayID.desc())

fig = plt.figure(figsize=(7, 7))

plot_pregame_players(d_replays[0], team, Team.DIRE, session, team_session, fig)
fig.tight_layout()
fig.savefig('pregame_route_dire.png')
fig.clf()
plot_pregame_players(r_replays[0], team, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig('pregame_route_radiant.png')
fig.clf()