from StaticAnalysis import session, team_session
from herotools.important_times import MAIN_TIME, ImportantTimes
from StaticAnalysis.analysis.Player import get_player_dataframe, get_team_dataframes, get_team_dataframes_rquery, _update_post_process, get_hero_winrate, get_hero_picks, _heroes_post_process
from sqlalchemy import or_
from StaticAnalysis.lib.team_info import get_player, TeamInfo, TeamPlayer
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.Replay import Replay
from pandas import DataFrame, concat
from functools import partial


def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team

def _simple_count_timecut(df: DataFrame, min_time=MAIN_TIME):
    '''
    Post processing helper for the team
    '''
    df['count'] = 1
    df = df.loc[df.loc[:, 'endGameTime'] >= min_time]
    df = df[['hero', 'count']].groupby(['hero']).sum()
    # df.columns = df.columns.droplevel(1)

    return df
hero_proc = partial(_simple_count_timecut, min_time=MAIN_TIME)

mouz = get_team(9338413)
comp_df = get_team_dataframes(
    mouz,
    [Player.hero, Player.endGameTime], post_process = hero_proc)

r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = mouz.get_replays(session).filter(r_filter)
comp_df_rquery = get_team_dataframes_rquery(
    mouz, r_query,
    [Player.hero, Player.win, Player.endGameTime], session, hero_proc)

comp_df = concat(comp_df, axis=1).fillna(0)
comp_df.columns = comp_df.columns.droplevel(1)

comp_df_rquery = concat(comp_df_rquery, axis=1).fillna(0)
comp_df_rquery.columns = comp_df_rquery.columns.droplevel(1)