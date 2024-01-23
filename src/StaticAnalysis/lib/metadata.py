from typing import Set

from sqlalchemy.sql import exists

from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Rune import Rune
from StaticAnalysis.replays.Scan import Scan
from StaticAnalysis.replays.Smoke import Smoke
from StaticAnalysis.replays.Ward import Ward
from StaticAnalysis.replays.Player import NetWorth


def make_meta(dataset="default"):
    if dataset is None:
        return {}

    meta = {
        'name': dataset,
        'time_cut': None,
        'leagues': None,
        'replays_dire': None,
        'drafts_only_dire': None,
        'replays_radiant': None,
        'drafts_only_radiant': None,

        'plot_dire_drafts': None,
        'plot_radiant_drafts': None,

        'plot_pos_dire': [],
        'plot_pos_radiant': [],
        'player_names': [],

        'plot_ward_dire': [],
        'plot_ward_radiant': [],
        'plot_ward_names': [],

        'wards_dire': {},
        'wards_radiant': {},

        'plot_scan_dire': None,
        'plot_scan_radiant': None,

        'plot_smoke_dire': None,
        'plot_smoke_radiant': None,

        'plot_draft_summary': None,
        'plot_hero_picks': None,
        'plot_pair_picks': None,
        'plot_pick_context': None,
        'plot_win_rate': None,
        'plot_rune_control': None,

        'stat_win_rate': None,

        'counter_picks': {}
    }

    return meta


def is_updated(session, r_query, team: TeamInfo,
               side: Team, metadata, has: None) -> tuple[bool, set]:
    side_filt = Replay.get_side_filter(team, side)
    replays = r_query.filter(side_filt)
    if has is None:
        replay_set = {r.replayID for r in replays}
    else:
        replay_set = {r.replayID for r in replays if has(session, r)}

    if metadata is None:
        return len(replay_set) != 0, replay_set
    else:
        return replay_set != set(metadata), replay_set


def has_type(session, replay: Replay, Type) -> bool:
    return session.query(exists().where(Type.replayID == replay.replayID)).scalar()


def has_picks(session, replay: Replay) -> bool:
    try:
        t0 = len(replay.teams[0].draft) > 0
        t1 = len(replay.teams[1].draft) > 0
    except IndexError:
        print(f"Invalid teams for {replay.replayID}")
        return False

    if t0 and t1:
        return True
    if t0:
        print("Missing pickbans for one team (1)")
    if t1:
        print("Missing pickbans for one team (0)")

    return False


def has_wards(session, replay: Replay) -> bool:
    return has_type(session, replay, Ward)


def has_runes(session, replay: Replay) -> bool:
    return has_type(session, replay, Rune)


def has_scans(session, replay: Replay) -> bool:
    return has_type(session, replay, Scan)


def has_smokes(session, replay: Replay) -> bool:
    return has_type(session, replay, Smoke)


def is_full_replay(session, replay: Replay) -> bool:
    '''Returns if replay is considered a complete one.
    At the moment this just requires player picks and wards.'''

    return has_picks(session, replay) and has_wards(session, replay)


def has_networth(session, replay: Replay) -> bool:
    '''Returns true if replay in session has a NetWorth object.'''
    return has_type(session, replay, NetWorth)