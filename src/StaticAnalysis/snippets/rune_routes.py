from StaticAnalysis import session, team_session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import PlayerStatus, Player
from StaticAnalysis.replays.Rune import Rune, RuneID
from herotools.important_times import MAIN_TIME, ImportantTimes
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from sqlalchemy import and_, or_
from pandas import read_sql
import numpy as np
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.analysis.visualisation import plot_player_positioning
from StaticAnalysis.analysis.route_vis import plot_player_paths
from StaticAnalysis.analysis.Player import player_position_replays, player_positioning_single
from StaticAnalysis.analysis.rune import wisdom_rune_times


def get_team(name) -> TeamInfo:
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team

team = get_team(2586976)
r_query = team.get_replays(session).filter(Replay.endTimeUTC >= ImportantTimes['Birmingham'])

start = 6.5 * 60
rune_times = wisdom_rune_times(r_query, max_time=13 * 60)
end = int(rune_times['game_time'].max())
# end = 550
test_query = player_position_replays(
    session, r_query, start=start, end=end
)

filter = (PlayerStatus.game_time > start,
              PlayerStatus.game_time <= 550)

query = (
    session.query(
        PlayerStatus.xCoordinate, PlayerStatus.yCoordinate, PlayerStatus.team_id,
        PlayerStatus.steamID, PlayerStatus.replayID, PlayerStatus.team, PlayerStatus.game_time
        )
        .filter(*filter)
        .join(r_query.subquery())
)

def player_position_single(
    session, r_query,
    team: TeamInfo, player: TeamPlayer,
    side: Team,
    start: int, end: int, recent_limit=None):

    t_filter = ()
    if start is not None:
        t_filter += (PlayerStatus.game_time >= start,)
    if end is not None:
        t_filter += (PlayerStatus.game_time <= end,)

    steam_id = player.player_id

    r_filter = Replay.get_side_filter(team, side)
    replays = r_query.filter(r_filter).subquery()
    if recent_limit is not None:
        replays = r_query.filter(r_filter).order_by(Replay.replayID.desc()).limit(recent_limit).subquery()

    p_filter = t_filter + (PlayerStatus.steamID == steam_id,
                            PlayerStatus.team == side)

    player_q = session.query(PlayerStatus)\
                        .filter(*p_filter)\
                        .join(replays)

    return player_q

p_query = player_position_single(
            session, r_query,
            team, team.players[0],
            Team.DIRE,
            start, end=550, recent_limit=5
        )
from pandas import DataFrame
def dataframe_xy(query, session) -> DataFrame:
    sql_query = query.with_entities(
        PlayerStatus.xCoordinate, PlayerStatus.yCoordinate,
        PlayerStatus.team_id, PlayerStatus.steamID, PlayerStatus.replayID,
        PlayerStatus.team, PlayerStatus.game_time).statement

    data = read_sql(sql_query, session.bind)

    return data

# table = dataframe_xy(p_query, session)

# from pandas import read_sql
# table2 = read_sql(query.statement, session.bind)

def player_position_replay_id(session, replay_id: int, start: int, end: int) -> DataFrame:
    '''
    More general player position table.
    start: int in seconds
    end: int in seconds
    '''
    filter = (
        PlayerStatus.replayID == replay_id,
        PlayerStatus.game_time > start,
        PlayerStatus.game_time <= end
        )

    query = (
        session.query(PlayerStatus.xCoordinate, PlayerStatus.yCoordinate, PlayerStatus.team_id,
                      PlayerStatus.steamID, PlayerStatus.replayID, PlayerStatus.team, PlayerStatus.game_time)
               .filter(*filter)
            #    .join(r_query.subquery())
    )

    pos_table = read_sql(query.statement, session.bind)

    return pos_table

data = []
r: Replay
for r in r_query:
    rune_max = rune_times[rune_times['replayID'] == r.replayID]['game_time'].max()
    rune_max = int(rune_max)
    data.append(player_position_replay_id(session, r.replayID,
                                          start=start, end=rune_max))

