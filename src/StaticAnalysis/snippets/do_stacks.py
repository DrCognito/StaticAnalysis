from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.update_plots import get_team
from StaticAnalysis.analysis.Replay import get_side_replays
from StaticAnalysis.analysis.route_vis import plot_pregame_players
import matplotlib.pyplot as plt
from herotools.important_times import MAIN_TIME
from StaticAnalysis import session, team_session
from sqlalchemy.orm import Session
from pandas import DataFrame, read_sql
from StaticAnalysis.lib.Common import get_player_name, get_player_name_simple
from StaticAnalysis.replays.Player import Kills, Deaths
from StaticAnalysis.replays.Rune import Rune, RuneID
from StaticAnalysis.analysis.Stacks import get_player_average_stacks, dump_stackies, get_team_average_stacks, get_roster_average_stacks, build_stack_dict
import matplotlib.pyplot as plt


r_filter = Replay.endTimeUTC >= MAIN_TIME
team: TeamInfo = get_team(9247354)
r_query = team.get_replays(session).filter(r_filter)
d_replays, r_replays = get_side_replays(r_query, session, team)

# r_query = session.query(Replay).filter(Replay.replayID == 8231394430)

p4 = get_player_average_stacks(team.players[3], r_query, session, None, 8*60)
p5 = get_player_average_stacks(team.players[4], r_query, session, None, 8*60)

set1r = lambda x: get_player_average_stacks(x, r_replays, session, None, 8*60)
set1d = lambda x: get_player_average_stacks(x, d_replays, session, None, 8*60)
p: TeamPlayer
for p in team.players:
    print(f"{p.player_id}, {p.name}: {set1r(p)}/{set1d(p)}")
    

set2r = lambda x: get_player_average_stacks(x, r_replays, session, 9*60, 15*60)
set2d = lambda x: get_player_average_stacks(x, d_replays, session, 9*60, 15*60)
p: TeamPlayer
for p in team.players:
    print(f"{p.player_id}, {p.name}: {set2r(p)}/{set2d(p)}")

# print(f"{team.players[4].name}, {team.players[4].player_id}")
# dump_stackies(team.players[4], r_query, session, 9*60, 15*60)

times = [(None, 8*60), (9*60, 15*60)]
labels = ('Before 8mins', '9 to 15mins')
r_dict = {
    p.name:[] for p in team.players
}
d_dict = {
    p.name:[] for p in team.players
}
for t0, t1 in times:
    procr = lambda x: get_player_average_stacks(x, r_replays, session, t0, t1)
    procd = lambda x: get_player_average_stacks(x, d_replays, session, t0, t1)
    for p in team.players:
        r_dict[p.name].append(procr(p))
        d_dict[p.name].append(procd(p))
        

r_dict = {}
d_dict = {}
# for (t0, t1), l in zip(times, labels):
#     procr = lambda x: get_player_average_stacks(x, r_replays, session, t0, t1)
#     procd = lambda x: get_player_average_stacks(x, d_replays, session, t0, t1)
#     r_dict[l] = [procr(p) for p in team.players]
#     r_dict[l].append(get_team_average_stacks(team, r_replays, session, t0, t1))
#     d_dict[l] = [procd(p) for p in team.players]
#     d_dict[l].append(get_team_average_stacks(team, d_replays, session, t0, t1))

r_dict = build_stack_dict(team, r_replays, session, times, labels)
d_dict = build_stack_dict(team, d_replays, session, times, labels)

fig, axes = plt.subplots(2, 1, figsize=(7, 7), layout='constrained', sharey=True)

# Make oneo f these 
# https://matplotlib.org/stable/gallery/lines_bars_and_markers/barchart.html
import numpy as np
x = np.arange(len(team.players) + 1)  # the label locations
width = 0.25  # the width of the bars
multiplier = 0

for player, stacks in r_dict.items():
    offset = width * multiplier
    rects = axes[0].bar(x + offset, stacks, width, label=player)
    axes[0].bar_label(rects, fmt='%.1f')
    multiplier += 1
names = [p.name for p in team.players] + ['Team',]

label_off = len(labels)*width*0.5
axes[0].set_xticks(x + width*0.5, names)
axes[0].set_ylabel('Average Stacks')
axes[0].set_title('Radiant')
axes[0].legend(loc='upper left', ncols=3)

multiplier = 0
for player, stacks in d_dict.items():
    offset = width * multiplier
    rects = axes[1].bar(x + offset, stacks, width, label=player)
    axes[1].bar_label(rects, fmt='%.1f')
    multiplier += 1

axes[1].set_xticks(x + width*0.5, names)
axes[1].set_ylabel('Average Stacks')
axes[1].set_title('Dire')
ymin, ymax = axes[1].get_ylim()
axes[1].set_ylim(ymin, 1.05*ymax)

# plt.show()
fig.savefig('stack_test.png')

# Standard error of the mean
# https://www.statology.org/standard-error-of-mean-python/