from herotools.important_times import MAIN_TIME
from StaticAnalysis import session, team_session
from sqlalchemy.orm import Session, Query
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.Stacks import PlayerStack
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Position import RolePosition
from sqlalchemy import select
from pandas import read_sql, read_sql_query, cut, IntervalIndex, Series
from herotools.lib.position import Position

r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = session.query(Replay).filter(r_filter)


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


def build_stack_dict_global(
    r_query: Query, session: Session, times: tuple[tuple[int, int]]
    ):
    from StaticAnalysis.replays.Position import get_unique_replayids
    
    min_time = min(t[0] for t in times)
    max_time = max(t[1] for t in times)
    time_bins = IntervalIndex.from_tuples(times, closed="right")
    # Get an extra row in the range as we deduct the minimum so this should be close enough.
    stack_query = (
        select(PlayerStack)
        .where(PlayerStack.game_time > min_time, PlayerStack.game_time <= max_time)
        .join(r_query.subquery())
    )
    stack_df = read_sql(stack_query, session.bind)
    # Reduce stacks by previous
    adjuster = lambda x: x.stacks - get_stacks_before(
        session, min_time, x.replayID, x.steamID)
    stack_df['stacks'] = stack_df.apply(adjuster, axis=1)
    stack_df['tBin'] = cut(stack_df['game_time'], time_bins)
    
    return stack_df
    # stack_df = read_sql(stack_query, session.bind)
    
times = ((-600, 9*60), (9*60, 15*60), (15*60, 200*60))

df = build_stack_dict_global(r_query, session, times)
radiant = df.loc[df['team'] == Team.RADIANT]
dire = df.loc[df['team'] == Team.DIRE]

def possify(session: Session, row: Series):
    replay_id = row.name[0]
    steamID = row.name[1]
    qry = select(RolePosition.position).where(
        RolePosition.replayID == replay_id,
        RolePosition.steamID == steamID
    )
    
    return session.scalar(qry)

rids = [r.replayID for r in r_query.all()]
qry = select(RolePosition).where(RolePosition.replayID.in_(rids))
role_pos = session.execute(qry).all()
p: RolePosition
pos_dict = {
    (p[0].replayID, p[0].steamID):p[0].position for p in role_pos
}

radiant['pos'] = radiant.apply(lambda x: pos_dict.get((x.replayID, x.steamID)), axis=1)
dire['pos'] = dire.apply(lambda x: pos_dict.get((x.replayID, x.steamID)), axis=1)