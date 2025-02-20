from StaticAnalysis import session, team_session
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.route_vis import plot_pregame_players, get_player_dataframes
from StaticAnalysis.analysis.smoke_vis import smoke_start_locale, smoke_end_locale_first, smoke_end_locale_individual, get_smoke_time_info
import matplotlib.pyplot as plt
from sqlalchemy import or_
from StaticAnalysis.vis.tormentor import plot_tormentor_kill_players

parivision = 9572001

def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team
team = get_team(parivision)
replays = team.get_replays(session)

replay: Replay
replay = replays[0]
side = replay.get_side(team)


test_df = get_player_dataframes(replays[0], side=side, session=session)


fig = plt.figure(figsize=(7, 7))




# Tormy kill time
tspawn = replay.tormentor_spawns[0].game_time
tkill = replay.tormentor_kills[0].game_time
spawn_location = (replay.tormentor_spawns[0].xCoordinate,replay.tormentor_spawns[0].yCoordinate)
max_time = tkill
min_time = tkill - 5*60

plot_tormentor_kill_players(
    replay, team, side, session, team_session,
    tkill, spawn_location, fig, time_slice=2*60)

fig.tight_layout()
fig.savefig("tormentor_2min.png")
fig.clf()
plot_tormentor_kill_players(
    replay, team, side, session, team_session,
    tkill, spawn_location, fig,time_slice=3*60)

fig.tight_layout()
fig.savefig("tormentor_3min.png")
fig.clf()

plot_tormentor_kill_players(
    replay, team, side, session, team_session,
    tkill, spawn_location, fig, time_slice=5*60)
fig.tight_layout()
fig.savefig("tormentor_5min.png")

min_time = tspawn - 1*60
time_slice = tkill - min_time
plot_tormentor_kill_players(
    replay, team, side, session, team_session,
    tkill, spawn_location, fig, time_slice=time_slice)
fig.tight_layout()
fig.savefig("tormentor_1minPreSpawn.png")