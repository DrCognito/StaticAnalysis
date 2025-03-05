from StaticAnalysis import session, team_session
from herotools.important_times import MAIN_TIME
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.lib.team_info import get_player, TeamInfo, TeamPlayer
from pandas import DataFrame, read_sql
from herotools.util import convert_to_32_bit, convert_to_64_bit
from sqlalchemy import or_

bzm_id = 93618577
bzm: TeamPlayer = get_player(bzm_id, team_session)

def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team


r_filter = Replay.endTimeUTC >= MAIN_TIME
tundra = get_team(8291895)
r_query = tundra.get_replays(session).filter(r_filter)

player_stats = session.query(Player, Player.win).join(r_query.subquery()).filter(Player.steamID == bzm.player_id)
player_df = read_sql(player_stats.statement, session.bind)
player_df['count'] = 1
player_df[['hero', 'count', 'win']].groupby(['hero']).sum()