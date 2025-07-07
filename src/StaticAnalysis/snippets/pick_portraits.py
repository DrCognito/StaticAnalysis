from StaticAnalysis import session, team_session
from herotools.important_times import MAIN_TIME
from StaticAnalysis.analysis.Player import get_player_dataframe, _heroes_post_process, get_team_dataframes, get_team_dataframes_rquery, _update_post_process, get_hero_winrate, get_hero_picks
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.lib.team_info import get_player, TeamInfo, TeamPlayer
from pandas import DataFrame, read_sql
from herotools.util import convert_to_32_bit, convert_to_64_bit
from sqlalchemy import or_
from propubs.libs.vis_comp import draw_recent_comp_record, TableStyle, process_team_portraits
from datetime import datetime, timedelta
from sqlalchemy.orm import Query, Session

bzm_id = 93618577
bzm: TeamPlayer = get_player(bzm_id, team_session)

def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team


r_filter = Replay.endTimeUTC >= MAIN_TIME
tundra = get_team(8291895)
gladiators = get_team(8599101)
spirit = get_team(7119388)
falcons = get_team(9247354)
execration = get_team(8254145)
r_query = spirit.get_replays(session).filter(r_filter)

# player_stats = session.query(Player.hero, Player.win, Player.endGameTime).join(r_query.subquery()).filter(Player.steamID == bzm.player_id)
# player_stats = session.query(Player.hero, Player.win, Player.endGameTime).filter(
#     Player.steamID == bzm.player_id, Player.endGameTime >= MAIN_TIME)
# player_df = read_sql(player_stats.statement, session.bind)
player_df = get_player_dataframe(bzm.player_id, [Player.hero, Player.win, Player.endGameTime])
player_df['count'] = 1
player_df_comp = player_df[['hero', 'count', 'win']].groupby(['hero']).sum()


row_bg_cycle = [(255, 255, 255, 255), (220, 220, 220, 255)]
style = TableStyle()
# test_line = draw_recent_comp_record(
#     player_df_comp, "Recent Competitive", background=row_bg_cycle[1], table_style=style
#     )


hero = 'npc_dota_hero_invoker'
now = datetime.now()
sevendaysago = now - timedelta(days=7)
fourteendaysago = now - timedelta(days=14)
testquery = session.query(Replay).filter(Replay.endTimeUTC >= fourteendaysago)
min_test = get_hero_winrate(bzm, hero, min_time = fourteendaysago)
qtest = get_hero_winrate(bzm, hero, r_query=testquery)
btest = get_hero_winrate(bzm, hero, min_time=MAIN_TIME, r_query=testquery)
ctest = get_hero_winrate(bzm, hero, min_time=sevendaysago, max_time=now, r_query=testquery)

def add_extra_cols(
    player: TeamPlayer | int, df: DataFrame, session: Session = session,
    r_query: Query = None) -> DataFrame:
    if df.empty:
        return df

    df['0to7 winrate'] = df.index.map(
        lambda x : get_hero_winrate(
            player, x, session, sevendaysago, now, r_query
            )
    )
    df['0to7 picks'] = df.index.map(
        lambda x : get_hero_picks(
            player, x, session, sevendaysago, now, r_query
            )
    )

    df['0to14 winrate'] = df.index.map(
        lambda x : get_hero_winrate(
            player, x, session, fourteendaysago, now, r_query
            )
    )
    # df['0to14 picks'] = df.index.map(
    #     lambda x : get_hero_picks(
    #         player, x, session, fourteendaysago, now, r_query
    #         )
    # )
    
    return df

hero='npc_dota_hero_silencer'


comp_df = get_team_dataframes_rquery(
    falcons, r_query,
    [Player.hero, Player.win, Player.endGameTime], session, _heroes_post_process)
for p in falcons.players:
    df = comp_df.get(p.name)
    if df is not None:
        add_extra_cols(p, df)
update_df = get_team_dataframes(
    falcons,
    [Player.hero, Player.win, Player.endGameTime], post_process = _update_post_process)
full_table = process_team_portraits(
    falcons,
    comp_df,
    update_df
)
full_table.save("falcons_table.png")