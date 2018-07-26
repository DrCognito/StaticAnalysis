from .Statistics import x_vs_time, xy_vs_time, cumulative_statistic
from pandas import DataFrame, Series
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.PositionTimeBase import PositionTimeBase
from replays.Replay import Replay, Team
from replays.Ward import Ward, WardType
from replays.TeamSelections import PickBans
from replays.Smoke import Smoke
from lib.team_info import TeamInfo
from sqlalchemy import and_


def win_rate_table(session, team):

    def _process_replays(r_in, side):
        total = len(r_in)
        wins = 0

        for game in r_in:
            if side == game.winner:
                wins += 1

        return wins, total - wins

    output = DataFrame(columns=['Win', 'Losses'])

    f_dire = Replay.get_side_filter(team, Team.DIRE)
    r_dire = team.get_replays(session, f_dire).all()
    output.loc['Dire'] = _process_replays(r_dire, Team.DIRE)

    f_radiant = Replay.get_side_filter(team, Team.RADIANT)
    r_radiant = team.get_replays(session, f_radiant).all()
    output.loc['Radiant'] = _process_replays(r_radiant, Team.RADIANT)

    output.loc['All'] = output.loc['Dire'] + output.loc['Radiant']
    output['Rate'] = output['Win'] / (output['Win'] + output['Losses'])

    return output


def get_smoke(r_query, session, team: TeamInfo):
    def _process_side(side):
        r_filter = Replay.get_side_filter(team, side)
        replays = r_query.filter(r_filter)

        w_query = session.query(Smoke).filter(Smoke.team == side)\
                                      .join(replays)

        return w_query

    return _process_side(Team.DIRE), _process_side(Team.RADIANT)


def hero_win_rate(r_query, team):
    output = DataFrame(columns=['Win', 'Loss'])

    def _process(side):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        for r in replays:
            is_win = r.winner == side

            picks = [p.hero for t in r.teams if t.team == side for p in t.draft]

            for hero in picks:
                column = 'Win' if is_win else 'Loss'

                if hero in output[column]:
                    output.loc[hero, column] += 1
                else:
                    output.loc[hero, column] = 1
                    other_col = 'Loss' if is_win else 'Win'
                    output.loc[hero, other_col] = 0

    _process(Team.DIRE)
    _process(Team.RADIANT)

    output.fillna(0, inplace=True)
    output['Total'] = output['Win'] + output['Loss']
    output['Rate'] = output['Win']/output['Total']

    return output


def get_ptbase_tslice(session, r_query, Type,
                      team: TeamInfo, start=None, end=None):
    if start is not None and end is not None:
        assert(end >= start)
        t_filter = and_(Type.game_time > start, Type.game_time <= end)
    elif start is not None:
        t_filter = Type.game_time > start
    elif end is not None:
        t_filter = Type.game_time <= end
    else:
        t_filter = None

    def _process_side(side):
        r_filter = Replay.get_side_filter(team, side)
        replays = r_query.filter(r_filter)

        if t_filter is not None:
            w_query = session.query(Type).filter(t_filter)\
                                         .filter(Type.team == side)\
                                         .join(replays)
        else:
            w_query = session.query(Type).filter(Type.team == side)\
                                         .join(replays)

        return w_query

    return _process_side(Team.DIRE), _process_side(Team.RADIANT)


def pair_rate(session, r_query, team):
    output = Series()

    def _process(side):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        for replay in replays:
            pick_pair = session.query(PickBans)\
                               .filter(PickBans.replayID == replay.replayID)\
                               .filter(PickBans.team == side,
                                       PickBans.is_pick == True)\
                               .order_by(PickBans.order.desc())\
                               .limit(2)

            pick_pair = [p.hero for p in pick_pair]
            if len(pick_pair) != 2:
                print("Skipped invalid hero picks.")
                continue
            pick_pair.sort()
            pair_str = pick_pair[0] + ", " + pick_pair[1]
            if pair_str in output:
                output[pair_str] += 1
            else:
                output[pair_str] = 1

    _process(Team.DIRE)
    _process(Team.RADIANT)
    output.sort_values(ascending=False, inplace=True)

    return output


