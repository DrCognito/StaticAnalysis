from datetime import datetime
from sqlalchemy.orm import Session, Query
from StaticAnalysis import session, CONFIG
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.Stacks import PlayerStack
from StaticAnalysis.replays.Replay import Replay, Team
from herotools.util import convert_to_64_bit
from StaticAnalysis.analysis.Replay import get_side_replays
import matplotlib.pyplot as plt
from pathlib import Path
from pandas import option_context, DataFrame, IntervalIndex
import numpy as np
from matplotlib.axes import Axes
from sqlalchemy import select
from pandas import read_sql, read_sql_query, cut
from typing import Iterable
from StaticAnalysis.replays.Position import RolePosition
from herotools.lib.position import Position

PLOT_BASE_PATH = CONFIG['output']['PLOT_OUTPUT']


def get_player_average_stacks(
    player: TeamPlayer | int, r_query: Query, session: Session = session,
    min_time: int = None, max_time: int = None, enforce_team: TeamInfo = None) -> float:
    if type(player) is int:
        steam_id = convert_to_64_bit(player)
    elif type(player) is TeamPlayer:
        steam_id = player.player_id

    stacks = []
    r: Replay
    for r in r_query:
        rid = r.replayID
        test_player = session.query(Player).filter(
            Player.replayID == rid, Player.steamID == steam_id).one_or_none()
        if test_player is None:
            if False:
                if type(player) is TeamPlayer:
                    print(f"[Stacks] Player {player.name}, {steam_id} missing for {rid}")
                else:
                    print(f"[Stacks] Player {steam_id} missing for {rid}")
            continue
        if enforce_team is not None:
            team_side = r.get_side(enforce_team)
            if team_side is None:
                print(f"[Stacks] {enforce_team.name} not found in {rid}")
            if test_player.team != team_side:
                if True:
                    if type(player) is TeamPlayer:
                        # print(f"[Stacks] Player {player.name}, {steam_id} wrong team for {rid}")
                        pass
                    else:
                        # print(f"[Stacks] Player {steam_id} wrong team for {rid}")
                        pass
                continue
        # Find how many to deduct first
        prior_stacks = 0
        if min_time is not None:
            s_query = session.query(PlayerStack).filter(
                PlayerStack.game_time < min_time, PlayerStack.steamID == steam_id,
                PlayerStack.replayID == rid
            ).order_by(PlayerStack.game_time.desc()).first()
            if s_query is not None:
                prior_stacks = s_query.stacks
        
        s_query = session.query(PlayerStack).filter(
                PlayerStack.game_time <= max_time, PlayerStack.steamID == steam_id,
                PlayerStack.replayID == rid
            ).order_by(PlayerStack.game_time.desc()).first()
        # Add the difference
        if s_query is not None:
            assert(s_query.stacks >= prior_stacks)
            stacks.append(s_query.stacks - prior_stacks)
        else:
            stacks.append(0)
    if len(stacks) == 0:
        return 0

    return np.mean(stacks)


def get_roster_average_stacks(
    team: TeamInfo, r_query: Query, session: Session = session,
    min_time: int = None, max_time: int = None) -> float:

    stacks = []
    player_ids = [p.player_id for p in team.players]
    for r in r_query:
        rid = r.replayID

        new_stacks = 0
        for steam_id in player_ids:
            prior_stacks = 0
            # Find how many to deduct first
            if min_time is not None:
                s_query = session.query(PlayerStack).filter(
                    PlayerStack.game_time < min_time, PlayerStack.steamID == steam_id,
                    PlayerStack.replayID == rid
                ).order_by(PlayerStack.game_time.desc()).first()
                if s_query is not None:
                    prior_stacks += s_query.stacks
        
            s_query = session.query(PlayerStack).filter(
                    PlayerStack.game_time <= max_time, PlayerStack.steamID == steam_id,
                    PlayerStack.replayID == rid
                ).order_by(PlayerStack.game_time.desc()).first()
            # Add the difference
            if s_query is not None:
                assert(s_query.stacks >= prior_stacks)
                new_stacks += s_query.stacks - prior_stacks

        stacks.append(new_stacks)
    if len(stacks) == 0:
        return 0

    return np.mean(stacks)


def get_team_average_stacks(
    team: TeamInfo, r_query: Query, session: Session = session,
    min_time: int = None, max_time: int = None) -> float:

    stacks = []
    r: Replay
    for r in r_query:
        team_side = r.get_side(team)
        rid = r.replayID
        if team_side is None:
            print(f"[Stacks] Could not find team {team.name} in replay {rid}")
            continue
        players  = session.query(Player).filter(
            Player.team == team_side, Player.replayID == rid).all()
        player_ids = [p.steamID for p in players]

        new_stacks = 0
        for steam_id in player_ids:
            prior_stacks = 0
            # Find how many to deduct first
            if min_time is not None:
                s_query = session.query(PlayerStack).filter(
                    PlayerStack.game_time < min_time, PlayerStack.steamID == steam_id,
                    PlayerStack.replayID == rid
                ).order_by(PlayerStack.game_time.desc()).first()
                if s_query is not None:
                    prior_stacks += s_query.stacks
        
            s_query = session.query(PlayerStack).filter(
                    PlayerStack.game_time <= max_time, PlayerStack.steamID == steam_id,
                    PlayerStack.replayID == rid
                ).order_by(PlayerStack.game_time.desc()).first()
            # Add the difference
            if s_query is not None:
                assert(s_query.stacks >= prior_stacks)
                new_stacks += s_query.stacks - prior_stacks

        stacks.append(new_stacks)
    if len(stacks) == 0:
        return 0

    return np.mean(stacks)


def dump_stackies(
    player: TeamPlayer | int, r_query: Query, session: Session = session,
    min_time: int = None, max_time: int = None):
    if type(player) is int:
        steam_id = convert_to_64_bit(player)
    elif type(player) is TeamPlayer:
        steam_id = player.player_id
        
    for r in r_query:
        rid = r.replayID
        # Find how many to deduct first
        prior_stacks = 0
        if min_time is not None:
            s_query = session.query(PlayerStack).filter(
                PlayerStack.game_time < min_time, PlayerStack.steamID == steam_id,
                PlayerStack.replayID == rid
            ).order_by(PlayerStack.game_time.desc()).first()
            if s_query is not None:
                prior_stacks = s_query.stacks
        
        s_query = session.query(PlayerStack).filter(
                PlayerStack.game_time <= max_time, PlayerStack.steamID == steam_id,
                PlayerStack.replayID == rid
            ).order_by(PlayerStack.game_time.desc()).first()
        # Add the difference
        if s_query is not None:
            assert(s_query.stacks >= prior_stacks)
            print(f"{rid}, {s_query.stacks - prior_stacks}")
        else:
            print(f"{rid}, 0")
        
    return


def build_stack_dict(
    team: TeamInfo, r_query: Query, session: Session,
    times: tuple[tuple[int, int]], labels: tuple[str]
    ) -> dict:
    assert(len(times) == len(labels))
    
    out_dict = {}
    for (t0, t1), l in zip(times, labels):
        proc = lambda x: get_player_average_stacks(
            x, r_query, session, t0, t1, enforce_team=team)
        out_dict[l] = [proc(p) for p in team.players]
        out_dict[l].append(get_team_average_stacks(team, r_query, session, t0, t1))

    return out_dict


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

    # Build table for each position
    positions = [
        Position.SAFE, Position.MID, Position.OFF,
        Position.P4, Position.P5
    ]
    from collections import defaultdict
    output = defaultdict(list)

    for tn, tb in zip(time_names, time_bins):
        for pos in positions:
            # Filter to position and game time then group by replay, take the maximum (cumulative here)
            # Then sum over the replays.
            # This is 0 result safe
            prior_stacks = (
                df[(df['game_time'] < tb[0]) & (df['pos'] == pos)]
                [['replayID','stacks']].groupby('replayID')
                .max().sum().iloc[0]
            )
            max_stacks = (
                df[(df['game_time'] <= tb[1]) & (df['pos'] == pos)]
                [['replayID','stacks']].groupby('replayID')
                .max().sum().iloc[0]
            )
            output[tn].append(
                float(max_stacks - prior_stacks)/total_replays
            )
    
    # Append the total for the team contribution as well. Not as complicated as with actual teams!
    for t in output:
        output[t].append(sum(output[t]))
    
    return output


def build_stack_dict_global(
    r_query: Query, session: Session, times: tuple[tuple[int, int], ...],
    labels: Iterable[str]
    ):

    min_time = min(t[0] for t in times)
    max_time = max(t[1] for t in times)
    # Get an extra row in the range as we deduct the minimum so this should be close enough.
    stack_query = (
        select(PlayerStack)
        .where(PlayerStack.game_time > min_time, PlayerStack.game_time <= max_time)
        .join(r_query.subquery())
    )
    stack_df = read_sql(stack_query, session.bind)
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
    # Remove nulls
    stack_df = stack_df[~stack_df['pos'].isnull()]
    
    # Process into output dictionaries
    tot_replays = stack_df['replayID'].nunique()
    # Both doubles replays as two sides a replay!
    both = proc_global_stack_df(stack_df, tot_replays*2, times, labels)
    radiant = (
        proc_global_stack_df(
            stack_df.loc[stack_df['team'] == Team.RADIANT],
            tot_replays, times, labels)
        )
    dire = (
        proc_global_stack_df(
            stack_df.loc[stack_df['team'] == Team.DIRE],
            tot_replays, times, labels)
        )
    
    return both, radiant, dire, tot_replays

STACK_TIMES = ((-600, 9*60), (9*60, 15*60), (15*60, 200*60))
STACK_LABELS = ('Before 9mins', '9 to 15mins', '≥ 15mins')


def do_stacks_global(r_query: Query, dataset: str, global_path: Path) -> dict:
    # Ensure path exists
    output_path = global_path / f"{dataset}"
    output_path.mkdir(parents=True, exist_ok=True)
    times = STACK_TIMES
    labels = STACK_LABELS
    both, radiant, dire, tot_replays = build_stack_dict_global(r_query, session, times, labels)
    names = ["P1", "P2", "P3", "P4", "P5", "Total"]
    global_json = {}
    
    # Radiant
    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')
    axe = plot_stacks(
        axe, radiant, names, "Radiant", tot_replays
    )
    destination = output_path / "radiant_stack_global.png"
    global_json['plot_radiant_stacks_global'] = f"{dataset}/radiant_stack_global.png"
    fig.savefig(destination)
    fig.clf()
    global_json['table_radiant_stacks'] = stack_html_table(radiant, names)
    
    # Dire
    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')
    axe = plot_stacks(
        axe, dire, names, "Dire", tot_replays
    )
    destination = output_path / "dire_stack_global.png"
    global_json['plot_dire_stacks_global'] = f"{dataset}/dire_stack_global.png"
    fig.savefig(destination)
    fig.clf()
    global_json['table_dire_stacks'] = stack_html_table(dire, names)
    
    return global_json


def do_stacks_team(team: TeamInfo, r_query, metadata: dict):
    d_replays, r_replays = get_side_replays(r_query, session, team)
    plot_base = Path(PLOT_BASE_PATH)
    team_path: Path = plot_base / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)
    
    times = STACK_TIMES
    labels = STACK_LABELS

    r_dict = build_stack_dict(team, r_replays, session, times, labels)
    d_dict = build_stack_dict(team, d_replays, session, times, labels)
    names = [p.name for p in team.players] + ['Team',]
    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')

    # Radiant
    # _process_side(r_dict, r_replays, "Radiant", axe)
    axe = plot_stacks(
        axe, r_dict, names, "Radiant", r_replays.count()
    )
    destination = team_path / "radiant/radiant_stack.png"
    metadata['plot_radiant_stacks'] = str(destination.relative_to(plot_base))
    fig.savefig(destination)
    fig.clf()
    
    # Dire
    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')
    axe = plot_stacks(
        axe, d_dict, names, "Dire", d_replays.count()
    )
    destination = team_path / "dire/dire_stack.png"
    metadata['plot_dire_stacks'] = str(destination.relative_to(plot_base))
    fig.savefig(destination)
    fig.clf()
    
    # Both
    fig, axes = plt.subplots(2, 1, figsize=(7, 7), layout='constrained', sharey=True)
    axe = plot_stacks(
        axes[0], r_dict, names, "Radiant", r_replays.count(), add_legend=False
    )
    axe = plot_stacks(
        axes[1], d_dict, names, "Dire", d_replays.count(), add_legend=False
    )
    destination = team_path / "summary_stack.png"
    if r_replays.count() != 0:
        ymin, ymax = axes[0].get_ylim()
        axes[0].set_ylim(ymin, 1.05*ymax)
        axes[0].legend(loc='upper left', ncols=3)
    else:
        # Render the info on the dire axis if no radiant replays.
        ymin, ymax = axes[1].get_ylim()
        axes[1].set_ylim(ymin, 1.05*ymax)
        axes[1].legend(loc='upper left', ncols=3)
    fig.savefig(destination)
    metadata['plot_summary_stacks'] = str(destination.relative_to(plot_base))
    
    # Table outputs option context handles precision
    with option_context('display.precision', 2):
        if r_replays.count() != 0:
            radiant_df = DataFrame(r_dict)
            radiant_df.index = names
            metadata['table_radiant_stacks'] = radiant_df.to_html()
        if d_replays.count() != 0:
            dire_df = DataFrame(d_dict)
            dire_df.index = names
            metadata['table_dire_stacks'] = dire_df.to_html()
    
    return metadata

def plot_stacks(
    axe: Axes, result_dict: dict[str,list[int]], names:list[str], title:str, total_games: int,
    width: float = 0.25, add_legend: bool=True) -> Axes:
    if total_games != 0:
        multiplier = 0
        x = np.arange(6) # 5 Players and a Total
        for label, stacks in result_dict.items():
                offset = width * multiplier
                rects = axe.bar(x + offset, stacks, width, label=label)
                axe.bar_label(rects, fmt='%.1f')
                multiplier += 1

        axe.set_xticks(x + width, names)
        axe.set_ylabel('Average Stacks')
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

    ymin, ymax = axe.get_ylim()
    axe.set_ylim(ymin, 1.05*ymax)
    if add_legend:
        axe.legend(loc='upper left', ncols=3)
    
    return axe


def stack_html_table(result_dict: dict[str,list[int]], names=Iterable[str]):
    with option_context('display.precision', 2):
        result_df = DataFrame(result_dict)
        result_df.index = names
        html = result_df.to_html()
    return html


def plot_stack_data(
    dict_in: dict, axe: Axes, names: list[str],
    width: float = 0.25, add_legend=True) -> Axes:
    multiplier = 0
    x = np.arange(6) # 5 Players and a Total
    for label, stacks in dict_in.items():
            offset = width * multiplier
            rects = axe.bar(x + offset, stacks, width, label=label)
            axe.bar_label(rects, fmt='%.1f')
            multiplier += 1

    axe.set_xticks(x + width, names)
    axe.set_ylabel('Average Stacks')
    axe.set_title('Radiant')

    return axe


