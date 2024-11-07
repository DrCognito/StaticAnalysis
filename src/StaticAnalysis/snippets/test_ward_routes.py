from StaticAnalysis import session, team_session
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.route_vis import plot_pregame_players
from StaticAnalysis.analysis.smoke_vis import smoke_start_locale, smoke_end_locale_first, smoke_end_locale_individual
import matplotlib.pyplot as plt
from StaticAnalysis.replays.Player import Player, PlayerStatus
from pandas import read_sql
from herotools.location import get_player_location

replay = session.query(Replay).filter(Replay.replayID == 7957516700).one()
nigma = team_session.query(TeamInfo).filter(TeamInfo.team_id == 7554697).one()
avulus = team_session.query(TeamInfo).filter(TeamInfo.team_id == 9498970).one()

fig = plt.figure(figsize=(7, 7))

plot_pregame_players(replay, nigma, Team.DIRE, session, team_session, fig)
fig.tight_layout()
fig.savefig("wardroute_dire.png")
fig.clf()

plot_pregame_players(replay, avulus, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig("wardroute_radiant.png")
fig.clf()

side = Team.DIRE
dire_player_loc = []
for player in replay.players:
    if player.team != side:
        continue
    query = player.status.filter(PlayerStatus.game_time <= 0)

    sql_query = query.with_entities(
        PlayerStatus.xCoordinate,
        PlayerStatus.yCoordinate,
        PlayerStatus.is_smoked,
        PlayerStatus.game_time,
        PlayerStatus.is_alive).statement

    p_df = read_sql(sql_query, session.bind)
    p_df['location'] = p_df.apply(
        lambda x: get_player_location(x['xCoordinate'], x['yCoordinate']),
        axis=1
        )
    dire_player_loc.append(p_df)

print(f"Smoke start: {smoke_start_locale(dire_player_loc)}")
print(f"Smoke end (by first break): {smoke_end_locale_first(dire_player_loc)}")
print(f"Smoke end (by everyones break): {smoke_end_locale_individual(dire_player_loc)}")
