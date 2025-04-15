from datetime import datetime
from sqlalchemy.orm import Session, Query
from StaticAnalysis import session, CONFIG
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.Stacks import PlayerStack
from StaticAnalysis.replays.Replay import Replay
from herotools.util import convert_to_64_bit
from StaticAnalysis.analysis.Replay import get_side_replays
import matplotlib.pyplot as plt
from pathlib import Path
from pandas import option_context, DataFrame
import numpy as np
from matplotlib.axes import Axes

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


def do_stacks(team: TeamInfo, r_query, metadata: dict):
    d_replays, r_replays = get_side_replays(r_query, session, team)
    plot_base = Path(PLOT_BASE_PATH)
    team_path: Path = plot_base / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)
    (team_path / 'dire').mkdir(parents=True, exist_ok=True)
    (team_path / 'radiant').mkdir(parents=True, exist_ok=True)
    
    times = [(None, 8*60), (9*60, 15*60)]
    labels = ('Before 8mins', '9 to 15mins')

    r_dict = build_stack_dict(team, r_replays, session, times, labels)
    d_dict = build_stack_dict(team, d_replays, session, times, labels)
    names = [p.name for p in team.players] + ['Team',]
    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')
    
    def _process_side(dict_in, q: Query, title:str, axe: Axes):
        if q.count() != 0:
            axe = plot_stack_data(dict_in, axe, names)
            axe.set_title(f"{title} ({q.count()} games)")
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
    _process_side(r_dict, r_replays, "Radiant", axe)
    ymin, ymax = axe.get_ylim()
    axe.set_ylim(ymin, 1.05*ymax)
    axe.legend(loc='upper left', ncols=3)
    destination = team_path / "radiant/radiant_stack.png"
    metadata['plot_radiant_stacks'] = str(destination.relative_to(plot_base))
    fig.savefig(destination)
    fig.clf()
    # Dire
    fig, axe = plt.subplots(figsize=(7, 3.5), layout='constrained')
    _process_side(d_dict, d_replays, "Dire", axe)
    ymin, ymax = axe.get_ylim()
    axe.set_ylim(ymin, 1.05*ymax)
    axe.legend(loc='upper left', ncols=3)
    destination = team_path / "dire/dire_stack.png"
    metadata['plot_dire_stacks'] = str(destination.relative_to(plot_base))
    fig.savefig(destination)
    fig.clf()
    # Both
    fig, axes = plt.subplots(2, 1, figsize=(7, 7), layout='constrained', sharey=True)
    _process_side(r_dict, r_replays, "Radiant", axes[0])
    _process_side(d_dict, d_replays, "Dire", axes[1])
    destination = team_path / "summary_stack.png"
    ymin, ymax = axes[0].get_ylim()
    axes[0].set_ylim(ymin, 1.05*ymax)
    axes[0].legend(loc='upper left', ncols=3)
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

    axe.set_xticks(x + width*0.5, names)
    axe.set_ylabel('Average Stacks')
    axe.set_title('Radiant')

    return axe


