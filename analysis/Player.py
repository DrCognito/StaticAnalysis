from .Statistics import x_vs_time, xy_vs_time
from datetime import timedelta
from pandas import Series, concat, DataFrame
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Player import Player, PlayerStatus
from replays.Replay import Replay, Team
from replays.TeamSelections import TeamSelections, PickBans
from sqlalchemy import and_, any_
from lib.team_info import TeamInfo


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

    for player in team.players:

        pid = player.player_id

        if p_filt is None:
            p_f = Player.steamID == pid
        else:
            p_f = and_(Player.steamID == pid, p_filt)

        p_picks = session.query(Player.hero).filter(p_f)\
                                            .join(Replay).filter(r_filt)

        p_res = Series(name=player.name)
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

    return concat(player_series, axis=1, sort=True).fillna(0)


def pick_context(hero, team, r_query, extra_p_filt=None):
    output = DataFrame(columns=['Pick', 'Ban',
                                'Opponent Pick', 'Opponent Ban'])

    def _process_context(side):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        player_filter = TeamSelections.draft.any(and_(PickBans.hero == hero,
                                                      PickBans.team == side,
                                                      PickBans.is_pick))

        if extra_p_filt is not None:
            player_filter = and_(player_filter, extra_p_filt)

        replays = replays.join(TeamSelections).filter(player_filter)
        print("Total: ", replays.count())

        for r in replays:
            picks_bans = [(x.hero, x.team, x.is_pick) for t in r.teams for x in t.draft]
            for pick in picks_bans:
                if pick[1] == side:
                    if pick[2]:
                        update = 'Pick'
                    else:
                        update = 'Ban'
                else:
                    if pick[2]:
                        update = 'Opponent Pick'
                    else:
                        update = 'Opponent Ban'

                if pick[0] in output[update]:
                    output.loc[pick[0], update] += 1
                else:
                    output.loc[pick[0], update] = 1

    _process_context(Team.DIRE)
    _process_context(Team.RADIANT)
    output.fillna(0, inplace=True)

    return output


def player_position(session, r_query, team: TeamInfo, player_slot: int,
                    start: int, end: int):

    t_filter = ()
    if start is not None:
        t_filter += (PlayerStatus.game_time >= start,)
    if end is not None:
        t_filter += (PlayerStatus.game_time <= end,)

    def _process_side(side):
        steam_id = team.players[player_slot].player_id

        r_filter = Replay.get_side_filter(team, side)
        replays = r_query.filter(r_filter)
        
        p_filter = t_filter + (PlayerStatus.steamID == steam_id,)

        player_q = session.query(PlayerStatus)\
                          .filter(*p_filter)\
                          .join(replays)
        
        return player_q

    return _process_side(Team.DIRE), _process_side(Team.RADIANT)