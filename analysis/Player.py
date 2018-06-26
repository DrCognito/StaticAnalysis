from .Statistics import x_vs_time, xy_vs_time
from datetime import timedelta
from pandas import Series, concat, DataFrame
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Player import Player
from replays.Replay import Replay, Team
from replays.TeamSelections import TeamSelections, PickBans
from sqlalchemy import and_, any_


def cumulative_player(session, prop_name, team, filt):

    players = session.query(Player).filter(filt)\
                                   .join(Replay).filter(team.filter)

    output = Series()
    count = team.replay_count(session)

    for p in players:
        off_set_time = p.replay.gameStart
        for prop in getattr(p, prop_name):
            time = timedelta(seconds=(prop.time - off_set_time))
            if time in output:
                output[time] += prop.increment
            else:
                output[time] = prop.increment

    if count > 0:
        output = output / count

    return output


def player_heroes(session, team, summarise=10, r_filt=None, p_filt=None):
    player_series = []

    if r_filt is None:
            r_filt = team.filter
    else:
        r_filt = and_(team.filter, r_filt)

    for player in team.player_ids:

        pid = team.player_ids[player]

        if p_filt is None:
            p_f = Player.steamID == pid
        else:
            p_f = and_(Player.steamID == pid, p_filt)

        p_picks = session.query(Player.hero).filter(p_f)\
                                            .join(Replay).filter(r_filt)

        p_res = Series(name=player)
        for pick in p_picks:
            if pick[0] in p_res:
                p_res[pick[0]] += 1
            else:
                p_res[pick[0]] = 1

        if summarise and len(p_res) > summarise:
            p_res.sort_values(ascending=False, inplace=True)
            other = p_res[summarise:].sum()
            p_res['Other'] = other
            p_res.sort_values(ascending=False, inplace=True)
            p_res = p_res[:summarise + 1]

        player_series.append(p_res)

    return concat(player_series, axis=1).fillna(0)


def pick_context(hero, team, r_query, extra_p_filt=None):
    output = DataFrame(columns=['Pick', 'Ban',
                                'Opponent Pick', 'Opponent Ban'])

    def _uprement(col, item):
        if item in col:
            col[item] += 1
        else:
            col[item] = 1

    def _process_context(side):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        player_filter = TeamSelections.draft.any(and_(PickBans.hero == hero,
                                                      PickBans.team == side,
                                                      PickBans.is_pick == True))

        if extra_p_filt is not None:
            player_filter = and_(player_filter, extra_p_filt)

        replays.filter(player_filter)

        for r in replays:
            picks_bans = [(x.hero, x.side, x.is_pick) for t in r.teams for x in t.draft]
            for pick in picks_bans:
                if pick[1] == side:
                    if pick[2] == True:
                        update = output['Pick']
                    else:
                        update = output['Ban']
                else:
                    if pick[2] == True:
                        update = output['Opponent Pick']
                    else:
                        update = output['Opponent Ban']

                if pick[0] in update:
                    update[pick[0]] += 1
                else:
                    update[pick[0]] = 1

    _process_context(Team.DIRE)
    _process_context(Team.RADIANT)

    return output
