from herotools.important_times import MAIN_TIME
from StaticAnalysis import session, team_session
from sqlalchemy.orm import Session, Query
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.Stacks import PlayerStack
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Position import RolePosition
from sqlalchemy import select
from pandas import read_sql, read_sql_query, cut, IntervalIndex, Series, DataFrame, option_context
from herotools.lib.position import Position
from typing import Iterable

r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = session.query(Replay).filter(r_filter)


def get_stacks_before(session: Session, before: int, replayID: int, steamID: int) -> int:
    qry = (
        select(PlayerStack.stacks)
        .where(
            PlayerStack.game_time < before,
            PlayerStack.steamID == steamID,
            PlayerStack.replayID == replayID)
        .order_by(PlayerStack.game_time.desc())
        )
    
    res = session.execute(qry).scalar()
    if res is None:
        res = 0
    
    return res


def proc_global_stack_df(
    df: DataFrame, total_replays: int, time_bins: Iterable, time_names: Iterable[str]):

    df = (
        df[['pos', 'tBin', 'stacks']]
        .groupby(['tBin', 'pos'], sort=False, observed=False)
        .sum()).sort_index()
    # Build table for each position
    positions = [
        Position.SAFE, Position.MID, Position.OFF,
        Position.P4, Position.P5
    ]
    from collections import defaultdict
    output = defaultdict(list)
    for pos in positions:
        p_series = df.xs(pos, level="pos") - df.xs(pos, level="pos").shift(fill_value=0)
        for tn, tb in zip(time_names, time_bins):
            output[tn].append(
                float(p_series.stacks[tb])/total_replays
            )
    
    # Append the total for the team contribution as well. Not as complicated as with actual teams!
    for t in output:
        output[t].append(sum(output[t]))
    
    return output


def build_stack_dict_global(
    r_query: Query, session: Session, times: tuple[tuple[int, int], ...],
    labels: Iterable[str]
    ):
    from StaticAnalysis.replays.Position import get_unique_replayids
    
    min_time = min(t[0] for t in times)
    max_time = max(t[1] for t in times)
    time_bins = IntervalIndex.from_tuples(times, closed="right")
    # Get an extra row in the range as we deduct the minimum so this should be close enough.
    stack_query = (
        select(PlayerStack)
        .where(PlayerStack.game_time > min_time, PlayerStack.game_time <= max_time)
        .join(r_query.subquery())
    )
    stack_df = read_sql(stack_query, session.bind)
    # Reduce stacks by all before minimum
    adjuster = lambda x: x.stacks - get_stacks_before(
        session, min_time, x.replayID, x.steamID)
    stack_df['stacks'] = stack_df.apply(adjuster, axis=1)
    stack_df['tBin'] = cut(stack_df['game_time'], time_bins)
    
    # Get the position dictionary for available replays from r_query dataset
    rids = [r.replayID for r in r_query.all()]
    qry = select(RolePosition).where(RolePosition.replayID.in_(rids))
    role_pos = session.execute(qry).all()
    p: RolePosition
    pos_dict = {
        (p[0].replayID, p[0].steamID):p[0].position for p in role_pos
    }
    # Apply dictionary
    stack_df['pos'] = stack_df.apply(lambda x: pos_dict.get((x.replayID, x.steamID)), axis=1)
    
    # Process into output dictionaries
    tot_replays = stack_df['replayID'].nunique()
    # Both doubles replays as two sides a replay!
    both = proc_global_stack_df(stack_df, tot_replays*2, time_bins, labels)
    radiant = (
        proc_global_stack_df(
            stack_df.loc[stack_df['team'] == Team.RADIANT],
            tot_replays, time_bins, labels)
        )
    dire = (
        proc_global_stack_df(
            stack_df.loc[stack_df['team'] == Team.DIRE],
            tot_replays, time_bins, labels)
        )
    
    return both, radiant, dire, stack_df
    # stack_df = read_sql(stack_query, session.bind)
    
times = ((-600, 9*60), (9*60, 15*60), (15*60, 200*60))
labels = ('Before 8mins', '9 to 15mins', '≥ 15mins')

both, radiant, dire, df = build_stack_dict_global(r_query, session, times, labels)

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from StaticAnalysis.analysis.Stacks import plot_stack_data
def do_stacks(result_dict: dict[str,list[int]], names:list[str], title:str, total_games: int):

    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')
    if total_games != 0:
        axe = plot_stack_data(result_dict, axe, names)
        axe.set_title(f"{title} ({total_games} games)")
    else:
        axe.text(
            0.5, 0.5, "No Data", fontsize=18,
            horizontalalignment='center',
            verticalalignment='center')
        axe.yaxis.set_ticks([])
        axe.xaxis.set_ticks([])
        axe.set_title(f"{title}")

        return axe

    # Radiant
    ymin, ymax = axe.get_ylim()
    axe.set_ylim(ymin, 1.05*ymax)
    axe.legend(loc='upper left', ncols=3)
    
    return axe


def stack_html_table(result_dict: dict[str,list[int]], names=Iterable[str]):
    result_df = DataFrame(result_dict)
    result_df.index = names
    return result_df.to_html()

tot_replays = df['replayID'].nunique()
names = ["P1", "P2", "P3", "P4", "P5", "Total"]
both_plot = do_stacks(both, names, "Combined", tot_replays)
radiant_plot = do_stacks(radiant, names, "Radiant", tot_replays)
dire_plot = do_stacks(dire, names, "Dire", tot_replays)