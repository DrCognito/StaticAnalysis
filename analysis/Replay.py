from .Statistics import x_vs_time, xy_vs_time, cumulative_statistic
from pandas import DataFrame, Series, concat
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


def simple_side_filter(r_query, session, team: TeamInfo,
                       Type, side: Team, extra_filter=None):
    r_filter = Replay.get_side_filter(team, side)
    replays = r_query.filter(r_filter)

    if extra_filter is not None:
        w_query = session.query(Type).filter(extra_filter)\
                                     .filter(Type.team == side)\
                                     .join(replays)
    else:
        w_query = session.query(Type).filter(Type.team == side)\
                                     .join(replays)

    return w_query


def get_smoke(r_query, session, team: TeamInfo):
    dire = simple_side_filter(r_query, session, team, Smoke, Team.DIRE)
    radiant = simple_side_filter(r_query, session, team, Smoke, Team.RADIANT)

    return dire, radiant


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

    dire = simple_side_filter(r_query, session, team, Type, Team.DIRE, t_filter)
    radiant = simple_side_filter(r_query, session, team, Type, Team.RADIANT, t_filter)

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

    return dire, radiant


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


def draft_summary(session, r_query, team) -> (DataFrame, DataFrame):
    '''Returns a count of picks and bans at each draft stage for team.
       Return type is Pandas DataFrame.
    '''

    def _process(side):
        output_pick = DataFrame()
        output_ban = DataFrame()

        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        replay = (t.draft for r in replays for t in r.teams if t.team == side)
        # for replay in replays:
        #     for t in replay.team:
        for draft in replay:
            picks = {}
            bans = {}
            pick_count = 0
            ban_count = 0

            for selection in draft:
                if selection.is_pick:
                    column = "Pick" + str(pick_count)
                    picks[column] = selection.hero
                    pick_count += 1
                else:
                    column = "Ban" + str(ban_count)
                    bans[column] = selection.hero
                    ban_count += 1

            output_pick = output_pick.append(picks, ignore_index=True)
            output_ban = output_ban.append(bans, ignore_index=True)

        return output_pick, output_ban

    dire = _process(Team.DIRE)
    radiant = _process(Team.RADIANT)

    output_pick = concat([dire[0], radiant[0]], ignore_index=True, sort=False)
    output_pick = output_pick.apply(Series.value_counts)
    output_ban = concat([dire[1], radiant[1]], ignore_index=True, sort=False)
    output_ban = output_ban.apply(Series.value_counts)

    return output_pick, output_ban
