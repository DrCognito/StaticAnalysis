from replays.Replay import Replay, Team
from lib.team_info import TeamInfo


def make_meta(dataset="default"):
    meta = {
        'name': dataset,
        'time_cut': None,
        'leagues': None,
        'replays_dire': None,
        'replays_radiant': None,

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
    }

    return meta


def is_updated(r_query, team: TeamInfo, metadata)-> (bool, bool):
    '''Check if the list of replays for a teams metadata matches
       the list of replays in the replay query.
       Returns result for (Dire, Radiant)
    '''
    def _test_side(side: Team):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        id_list = {r.replayID for r in replays}

        side_str = 'replays_dire' if side == Team.DIRE else 'replays_radiant'
        if metadata[side_str] is None:
            return len(id_list) != 0, id_list

        return id_list != set(metadata[side_str]), id_list

    new_dire, dire_list = _test_side(Team.DIRE)
    new_radiant, radiant_list = _test_side(Team.RADIANT)

    return new_dire, dire_list, new_radiant, radiant_list
