from operator import or_
from .Statistics import x_vs_time, xy_vs_time
from datetime import timedelta
from pandas import Series, concat, DataFrame, read_sql
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Player import Player, PlayerStatus
from replays.Replay import Replay, Team
from replays.TeamSelections import TeamSelections, PickBans
from sqlalchemy import and_, any_
from lib.team_info import TeamInfo
from sqlalchemy.orm.query import Query
from sqlalchemy.orm import Session
from cache.player_pos import PlayerPosIndex, PlayerPos, is_cached, get_dataframe


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


def player_heroes(session, team, summarise=10,
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

        if summarise and len(p_res) > summarise:
            p_res.sort_values(ascending=False, inplace=True)
            other = p_res[summarise:].sum()
            p_res['Other'] = other
            p_res.sort_values(ascending=False, inplace=True)
            p_res = p_res[:summarise + 1]

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


PP_VERSION = 1

def get_dataframe(session: Session, replay_id: int, steam_id: int, cache=True) -> DataFrame:
    query = session.query(PlayerStatus).filter(PlayerStatus.replayID == replay_id,
                                               PlayerStatus.steamID == steam_id)
    if query.count() == 0:
        return DataFrame()

    sql_query = query.with_entities(PlayerStatus.xCoordinate,
                                    PlayerStatus.yCoordinate).statement
    df = read_sql(sql_query, session.bind)
def player_position_table(session: Session, r_query: Query, team: TeamInfo, steam_id: int,
                          start: int, end: int, side: Team,
                          cache_sess: Session, limit=None) -> DataFrame:
    # Get replayIDs
    side_filt = Replay.get_side_filter(team, side)
    replays = r_query.filter(side_filt)
    if limit is not None:
        replays = replays.limit(limit)
    replay_ids = [r[0] for r in replays.with_entities(Replay.replayID).all()]
    cached = []
    new = []
    for r in replay_ids:
        if is_cached(cache_sess, r, steam_id, PP_VERSION):
            cached.append(r)
        else:
            new.append(r)

    dfs = []
    dfs.append(get_dataframe(cache_sess, cached, steam_id))