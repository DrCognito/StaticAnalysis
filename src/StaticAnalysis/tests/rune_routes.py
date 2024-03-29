from StaticAnalysis import session, team_session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import PlayerStatus, Player
from StaticAnalysis.replays.Rune import Rune, RuneID
from herotools.important_times import MAIN_TIME
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from sqlalchemy import and_, or_
from pandas import read_sql
import numpy as np
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.analysis.visualisation import plot_player_positioning
from StaticAnalysis.analysis.route_vis import plot_player_paths


def get_team(name) -> TeamInfo:
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team

team = get_team(2586976)
r_query = team.get_replays(session).filter(Replay.endTimeUTC >= MAIN_TIME)

t_filter = (PlayerStatus.game_time > 7 * 60 - 30,
            PlayerStatus.game_time <= 7 * 60 + 10)
p_query = (session.query(PlayerStatus.xCoordinate, PlayerStatus.yCoordinate,
                         PlayerStatus.team_id, PlayerStatus.steamID, PlayerStatus.team, PlayerStatus.replayID)
                  .join(r_query.subquery()).filter(*t_filter)
)
t_query = (session.query(PlayerStatus)
                  .join(r_query.subquery()).filter(*t_filter)
)

p_pos = read_sql(p_query.statement, session.bind)
# lanes = pos_df.groupby(by=['team', 'hero',])['lane'].apply(lambda x: x.value_counts().index[0])
r_ids = {x.replayID for x in r_query}
p2_query = (
    session.query(PlayerStatus.xCoordinate, PlayerStatus.yCoordinate,
                  PlayerStatus.team_id, PlayerStatus.steamID)
                 .filter(PlayerStatus.replayID.in_(r_ids))
                 .filter(*t_filter)
)

tesT_id = 7287618636
t2_query = (session.query(PlayerStatus)
                  .filter(PlayerStatus.replayID == tesT_id).filter(*t_filter)
)
p2_pos = read_sql(t2_query.statement, session.bind)
print(p2_pos.team_id.unique())

from sqlalchemy import select
from StaticAnalysis.replays.TeamSelections import TeamSelections
blah = ( 
        select([TeamSelections.teamID])
        .where(TeamSelections.replay_ID == 7287618636)
        .where(TeamSelections.team == Team.RADIANT)
)
p_grp = p_pos.groupby(['steamID', 'team_id']).agg(list)
p_grp.xs(2586976, level=1)

t_player = team_session.query(TeamPlayer).filter(TeamPlayer.player_id == 76561198053884305)

import timeit
# Get player ids manually
start_time = timeit.default_timer()
player_query = session.query(Player).filter(Player.replayID == 7287618636)
players_queries = [(p.steamID, p.team) for p in player_query]
print(timeit.default_timer() - start_time)

# Get player ids from our table
filtered_tab = p_pos.loc[p_pos['replayID'] == 7287618636]
start_time = timeit.default_timer()
#.groupby(['steamID']).agg(min)
players_filt = filtered_tab.loc[:, ["steamID", "team"]].drop_duplicates()
ft_players = list(players_filt.itertuples(index=False, name=None))
print(timeit.default_timer() - start_time)

rune_query = (    
    session.query(Rune.game_time, Rune.replayID)
                  .join(r_query.subquery())
                  .filter(Rune.runeType == RuneID.Wisdom, Rune.game_time < 13 * 60)
)