from StaticAnalysis.replays.TwinGate import TwinGate
from pandas import DataFrame, IntervalIndex, cut
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import seaborn as sns
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.analysis.Replay import get_side_replays
from itertools import chain
from sqlalchemy.orm import Query, Session
from pathlib import Path
from StaticAnalysis import CONFIG
import matplotlib.pyplot as plt

PLOT_BASE_PATH = CONFIG['output']['PLOT_OUTPUT']
sns.set_theme(font_scale=1.0)

def get_dataframe_counts(r_query: Query, team, session) -> tuple[DataFrame, dict[str, int]]:
    '''
    Builds a set of gate transitions from the set of replays requiring team matching to team in
    TwinGate so the team should be correct!
    Returns DataFrame and team specific player game counts.
    '''
    pid_map = {p.player_id:p.name for p in team.players}
    counts = {}
    gate_list = []
    for p in team.players:
        counts[p.name] = 0
        d_replays, r_replays = get_side_replays(r_query, session, team)
        d_replays, r_replays = d_replays.subquery(), r_replays.subquery()

        # Radiant
        r_gates = session.query(TwinGate).filter(
            TwinGate.hero_team == Team.RADIANT, TwinGate.steamID == p.player_id
        ).join(r_replays)
        counts[p.name] += session.query(Player).filter(
            Player.steamID == p.player_id, Player.team == Team.RADIANT).join(r_replays).count()

        # Dire
        d_gates = session.query(TwinGate).filter(
            TwinGate.hero_team == Team.DIRE, TwinGate.steamID == p.player_id
        ).join(d_replays)
        counts[p.name] += session.query(Player).filter(
            Player.steamID == p.player_id, Player.team == Team.DIRE).join(d_replays).count()

        gate_list += [
            {'steamID': g.steamID, 'time':g.channel_start, 'gate side':g.side_pos,
            'name': pid_map[g.steamID]} for g in chain(r_gates, d_gates)
        ]

    return DataFrame(gate_list), counts


def add_count(ax: Axes, count: dict[str, int], offset = -0.1) -> Axes:
    '''
    Adds the counts in count to Axes ax at the offset.
    '''
    # Add "games"
    y_font = ax.get_yticklabels()[0].get_fontproperties()
    ax.text(
        x=-0.1, y=-0.1, s='Games',
        ha='right', va='baseline',
        fontproperties=y_font)
    offset = -0.1
    for tex in ax.get_xticklabels():
        c = count[tex.get_text()]
        fp = tex.get_fontproperties()
        ax.text(y=offset, x=tex.get_position()[0], s=c, ha='center',
            fontproperties=fp)
    
    return ax


def plot_twingate_table(ax: Axes, df: DataFrame, num_fmt: str) -> Axes:
    sns.heatmap(df, annot=True, fmt=num_fmt, linewidths=.5, ax=ax)
    ax.set(xlabel="", ylabel="")
    ax.xaxis.tick_top()
    ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=0, ha='center')
    ax.xaxis.set_tick_params(pad=15.0)
    ax.xaxis.set_ticks_position('none')
    ax.set_yticks(ax.get_yticks(), ax.get_yticklabels(), rotation=0, ha='right')
    
    return ax


tg_time_binning = IntervalIndex.from_tuples([
    (4*60, 8*60), # 4 to 8mins
    (8*60, 20*60), # 8 to 20mins
    (20*60, 30*60), # 20 to 30mins
    (30*60, 40*60), # 30 to 40mins
    (40*60, 400*60) # 40+
    ])
tg_time_names = [
    "4 to 8mins",
    "8 to 20mins",
    "20 to 30mins",
    "30 to 40mins",
    ">40mins",
]
tg_time_map = {k:v for k,v in zip(tg_time_binning, tg_time_names)}


def do_twin_gates(
    team: TeamInfo, r_query: Query, session: Session, metadata: dict) -> dict:
    # Initial plot setup
    plot_base = Path(PLOT_BASE_PATH)
    team_path: Path = plot_base / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)

    pid_map = {p.player_id:p.name for p in team.players}
    # Get data
    df, game_counts = get_dataframe_counts(r_query, team, session)
    if df.empty:
        metadata['plot_twingate_move'] = None
        return metadata

    # Setup the DataFrame
    df['tBin'] = cut(df['time'], tg_time_binning)
    # Labels wont work on IntervalIndex
    df['tBin'] = df['tBin'].map(tg_time_map)
    df['name'] = df['steamID'].map(pid_map)
    df['count'] = 1
    
    # Pivot table to per time interval representation
    df = (df[['name', 'tBin', 'count']]
        .pivot_table(index='tBin', columns='name', aggfunc='sum', observed=True)
        )
    # Remove extraneous count multicol
    df.columns = list(zip(*df.columns))[1]
    # Reorder the columns to match names, this is a full copy apparently!
    df = df.reindex(columns=[p.name for p in team.players])
    # Some times NaNs can show up for some reason, handle them
    df = df.fillna(0).astype(int)
    
    # Figure setup
    fig = plt.figure(figsize=(8, 8), layout="compressed")
    (ax1, ax2) = fig.subplots(nrows=2)
    # Do total
    ax1 = plot_twingate_table(ax1, df, "d")
    ax1 = add_count(ax1, game_counts)
    ax1.set_title("Total", pad=20)
    
    # Do fractional
    for col in df.columns:
        df[col] = df[col] / game_counts[col]
    ax2 = plot_twingate_table(ax2, df, ".2f")
    ax2 = add_count(ax2, game_counts)
    ax2.set_title("Average", pad=20)
    
    destination = team_path / 'twin_gate_transitions.png'
    fig.savefig(destination)
    metadata['plot_twingate_move'] = str(destination.relative_to(plot_base))
    
    return metadata