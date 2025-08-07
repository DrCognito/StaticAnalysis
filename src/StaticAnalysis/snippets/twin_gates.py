from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TwinGate import TwinGate
from herotools.important_times import MAIN_TIME
from pandas import DataFrame, IntervalIndex, cut
import matplotlib.pyplot as plt
import seaborn as sns
from StaticAnalysis.lib.Common import seconds_to_nice
falcons = get_team(9247354)
spirit = get_team(7119388)
team = spirit
pids = [p.player_id for p in team.players]
pid_map = {p.player_id:p.name for p in team.players}
replays = session.query(Replay).filter(
    team.filter, Replay.endTimeUTC > MAIN_TIME 
)
n_replays = replays.count()
q_gate = session.query(TwinGate).filter(TwinGate.steamID.in_(pids)).join(replays.subquery())
gate_list = [
    {'steamID': p.steamID, 'time':p.channel_start, 'gate side':p.side_pos,
     'name': pid_map[p.steamID] + f'\n{n_replays}'} for p in q_gate
    ]
test_df = DataFrame(gate_list)

time_binning = [
    (4*60, 8*60), # 4 to 8mins
    (8*60, 20*60), # 8 to 20mins
    (20*60, 30*60), # 20 to 30mins
    (30*60, 40*60), # 30 to 40mins
    (40*60, 400*60) # 40+
    ]
time_names = [
    "4 to 8mins",
    "8 to 20mins",
    "20 to 30mins",
    "30 to 40mins",
    ">40mins",
]
#t_binning = interval_range(0, 30*60, 3)
time_binning = IntervalIndex.from_tuples(time_binning)
time_map = {k:v for k,v in zip(time_binning, time_names)}
test_df['tBin'] = cut(test_df['time'], time_binning)
test_df['tBin'] = test_df['tBin'].map(time_map)
test_df['name'] = test_df['steamID'].map(pid_map)
test_df['count'] = 1

test_pivot = test_df[['name', 'tBin', 'count']].pivot_table(index='tBin', columns='name', aggfunc='sum', observed=True)
# Remove extraneous count multicol
test_pivot.columns = list(zip(*test_pivot.columns))[1]
# Reorder the columns to match names, this is a full copy apparently!
test_pivot = test_pivot.reindex(columns=[p.name for p in team.players])
# test_pivot.columns = [p.name for p in team.players]
test_pivot = test_pivot.fillna(0).astype(int)
sns.set_theme(font_scale=1.5)
# Draw a heatmap with the numeric values in each cell
fig = plt.figure(figsize=(18, 6), layout="constrained")
(ax1, ax2) = fig.subplots(ncols=2)


def add_count(ax, count: list[int]):
    # Add "games"
    ax.text(x=-0.1, y=-0.1, s='Games', ha='right', va='baseline')
    offset = -0.1
    for c, p in zip(count, ax.get_xticks()):
        ax.text(y=offset, x=p, s=c, ha='center')
    
    return ax

sns.heatmap(test_pivot, annot=True, fmt="d", linewidths=.5, ax=ax1)
ax1.set(xlabel="", ylabel="")
ax1.xaxis.tick_top()
ax1.set_xticks(ax1.get_xticks(), ax1.get_xticklabels(), rotation=0, ha='center')
ax1.xaxis.set_tick_params(pad=25.0)
ax1.xaxis.set_ticks_position('none')
add_count(ax1, [n_replays]*5)
ax1.set_yticks(ax1.get_yticks(), ax1.get_yticklabels(), rotation=0, ha='right')
ax1.set_title("Total", pad=20)

test_frac = test_pivot/replays.count()
sns.heatmap(test_frac, annot=True, fmt=".2f", linewidths=.5, ax=ax2)
ax2.set(xlabel="", ylabel="")
ax2.xaxis.tick_top()
ax2.set_xticks(ax2.get_xticks(), ax2.get_xticklabels(), rotation=0, ha='center')
ax2.xaxis.set_ticks_position('none')
ax2.xaxis.set_tick_params(pad=25.0)
add_count(ax2, [n_replays]*5)
ax2.set_yticks(ax2.get_yticks(), ax2.get_yticklabels(), rotation=0, ha='right')
ax2.set_title("Average", pad=20)

fig.savefig("twin_gates.png")

# replays = session.query(Replay).filter(Replay.replayID == 8368604072)
# q_gate = session.query(TwinGate).filter(TwinGate.steamID.in_(pids)).join(replays.subquery())
# gate_list = [
#     {'name': pid_map[p.steamID], 'time':seconds_to_nice(p.channel_end), 'gate side':p.side_pos,
#      } for p in q_gate
#     ]
# df = DataFrame(gate_list)
# print(df)