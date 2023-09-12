from datetime import timedelta
from operator import or_

from pandas import DataFrame, Series, concat, read_sql
from sqlalchemy import and_

from StaticAnalysis.lib.Common import distance_between
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Player import Player, PlayerStatus
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.TeamSelections import PickBans, TeamSelections


def cumulative_player(session, prop_name, team, filt):

    players = session.query(Player).filter(filt)\
                                   .join(Replay).filter(team.filter)

    output = Series(dtype='UInt16')
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


def player_heroes(session, team, nHeroes=10, summarise=False,
                  r_filt=None, p_filt=None, limit=None):
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

        replays = session.query(Replay).filter(r_filt)
        if limit is not None:
            replays = replays.order_by(Replay.replayID.desc()).limit(limit)
        p_picks = session.query(Player.hero).filter(p_f)\
                                            .join(replays)

        p_res = Series(name=player.name, dtype='UInt16')
        for pick in p_picks:
            if pick[0] in p_res:
                p_res[pick[0]] += 1
            else:
                p_res[pick[0]] = 1

        if summarise and len(p_res) > nHeroes:
            p_res.sort_values(ascending=False, inplace=True)
            other = p_res[nHeroes:].sum()
            p_res['Other'] = other
            p_res.sort_values(ascending=False, inplace=True)
            p_res = p_res[:nHeroes + 1]
        else:
            p_res = p_res.head(nHeroes)

        player_series.append(p_res)

    return concat(player_series, axis=1, sort=True).fillna(0)


def pick_context(hero, team, r_query, extra_p_filt=None, limit=None):
    output = DataFrame(columns=['Pick', 'Ban',
                                'Opponent Pick', 'Opponent Ban'])

    team_filter = or_(TeamSelections.teamID == team.team_id,
                      TeamSelections.stackID.in_([team.stack_id, team.extra_stackid]))
    pick_filter = TeamSelections.draft.any(and_(PickBans.hero == hero, PickBans.is_pick))
    pick_filter = and_(team_filter, pick_filter)
    if limit is not None:
        latest5 = [r.replayID for r in r_query.order_by(Replay.replayID.desc()).limit(limit)]
        pick_filter = and_(TeamSelections.replay_ID.in_(latest5), pick_filter)
    if extra_p_filt is not None:
        pick_filter = and_(pick_filter, extra_p_filt)
    replays = r_query.join(TeamSelections, TeamSelections.replay_ID == Replay.replayID).filter(pick_filter)

    for r in replays:
        found_hero = False
        for t in r.teams:
            if (t.teamID != team.team_id and
                t.stackID != team.stack_id and
                t.stackID != team.extra_stackid):
                opponent = True
            else:
                opponent = False
            picks_bans = [(x.hero, x.is_pick) for x in t.draft]
            for h_in, is_pick in picks_bans:
                if h_in == hero:
                    assert(not opponent)
                    found_hero = True
                    continue
                if not opponent:
                    if is_pick:
                        update = 'Pick'
                    else:
                        update = 'Ban'
                else:
                    if is_pick:
                        update = 'Opponent Pick'
                    else:
                        update = 'Opponent Ban'

                if h_in in output[update]:
                    output.loc[h_in, update] += 1
                else:
                    output.loc[h_in, update] = 1
        if not found_hero:
            print(f"Failed to find {hero} in {r.replayID}")
            #raise AssertionError
        #assert(found_hero)

    output.fillna(0, inplace=True)

    return output


def player_position(session, r_query, team: TeamInfo, player_slot: int,
                    start: int, end: int, recent_limit=5):

    t_filter = ()
    if start is not None:
        t_filter += (PlayerStatus.game_time >= start,)
    if end is not None:
        t_filter += (PlayerStatus.game_time <= end,)

    def _process_side(side):
        steam_id = team.players[player_slot].player_id

        r_filter = Replay.get_side_filter(team, side)
        replays = r_query.filter(r_filter).subquery()
        replays_limited = r_query.filter(r_filter).order_by(Replay.replayID.desc()).limit(recent_limit).subquery()

        p_filter = t_filter + (PlayerStatus.steamID == steam_id,)

        player_q = session.query(PlayerStatus)\
                          .filter(*p_filter)\
                          .join(replays)

        player_q_limited = session.query(PlayerStatus)\
                                  .filter(*p_filter)\
                                  .join(replays_limited)

        return player_q, player_q_limited

    return _process_side(Team.DIRE), _process_side(Team.RADIANT)


def player_position_replays(session, r_query, start: int, end: int, extra_filter: tuple = None) -> DataFrame:
    '''
    More general player position table.
    start: int in seconds
    end: int in seconds
    extra_filter: tuple that is added to time filter
    '''
    filter = (PlayerStatus.game_time > start,
              PlayerStatus.game_time <= end)
    if extra_filter is not None:
        filter += extra_filter

    query = (
        session.query(PlayerStatus.xCoordinate, PlayerStatus.yCoordinate, PlayerStatus.team_id,
                      PlayerStatus.steamID, PlayerStatus.replayID, PlayerStatus.team)
               .join(r_query.subquery())
               .filter(*filter)
    )

    pos_table = read_sql(query.statement, session.bind)

    return pos_table


def player_positioning_single(session, replay_id, team: TeamInfo, steam_id: int,
                              start: int, end: int, alive_only=None):
    t_filter = ()
    if start is not None:
        t_filter += (PlayerStatus.game_time >= start,)
    if end is not None:
        t_filter += (PlayerStatus.game_time <= end,)
    if alive_only is not None:
        t_filter += (PlayerStatus.is_alive == alive_only)

    # steam_id = team.players[player_slot].player_id
    p_filter = t_filter + (PlayerStatus.steamID == steam_id, PlayerStatus.replayID == replay_id)

    return session.query(PlayerStatus).filter(*p_filter)


def player_positioning_replay(session, replay_id, start: int, end: int, alive_only=None):
    t_filter = ()
    if start is not None:
        t_filter += (PlayerStatus.game_time >= start,)
    if end is not None:
        t_filter += (PlayerStatus.game_time <= end,)
    if alive_only is not None:
        t_filter += (PlayerStatus.is_alive == alive_only, )

    # steam_id = team.players[player_slot].player_id
    p_filter = t_filter + (PlayerStatus.replayID == replay_id, )

    return session.query(PlayerStatus).filter(*p_filter)


def closest_tower(position: tuple, tower_dict, scheme=['top', 'mid', 'bottom']):
    t_dist = 99999999999999
    name = "Fixme"
    for tower in scheme:
        t_cord = tower_dict[tower]
        if (dist := distance_between(position, t_cord)) < t_dist:
            t_dist = dist
            name = tower

    return name
