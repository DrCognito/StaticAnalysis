from StaticAnalysis import session, team_session
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.route_vis import plot_pregame_players, get_player_dataframes
from StaticAnalysis.analysis.smoke_vis import smoke_start_locale, smoke_end_locale_first, smoke_end_locale_individual, get_smoke_time_info
import matplotlib.pyplot as plt
from StaticAnalysis.replays.Player import Player, PlayerStatus
from pandas import read_sql
from herotools.location import get_player_location
from StaticAnalysis.analysis.draft_vis import process_team_portrait
from StaticAnalysis.replays.TeamSelections import TeamSelections

replay = session.query(Replay).filter(Replay.replayID == 7957516700).one()
nigma = team_session.query(TeamInfo).filter(TeamInfo.team_id == 7554697).one()
avulus = team_session.query(TeamInfo).filter(TeamInfo.team_id == 9498970).one()

glad_test1 = session.query(Replay).filter(Replay.replayID == 8011119646).one()
glad_test2 = session.query(Replay).filter(Replay.replayID == 8009585260).one()
gladiators = team_session.query(TeamInfo).filter(TeamInfo.team_id == 8599101).one()
glad_select1 = session.query(TeamSelections).filter(
    TeamSelections.replay_ID == 8011119646 and TeamSelections.teamID == gladiators.team_id)
glad_select2 = session.query(TeamSelections).filter(
    TeamSelections.replay_ID == 8009585260 and TeamSelections.teamID == gladiators.team_id)
fig = plt.figure(figsize=(7, 7))

plot_pregame_players(glad_test1, gladiators, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig("wardroute_glad1.png")
fig.clf()

plot_pregame_players(glad_test2, gladiators, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig("wardroute_glad2.png")
fig.clf()

side = Team.RADIANT
glad_df1 = get_player_dataframes(glad_test1, side, session)
glad_df2 = get_player_dataframes(glad_test2, side, session)

print(f"Smoke start: {smoke_start_locale(glad_df2)}")
print(f"Smoke end (by first break): {smoke_end_locale_first(glad_df2)}")
print(f"Smoke end (by everyones break): {smoke_end_locale_individual(glad_df2)}")
print(get_smoke_time_info(glad_df2))

test_table = get_smoke_time_info(glad_df2)