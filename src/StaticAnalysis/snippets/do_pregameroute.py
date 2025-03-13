from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.update_plots import get_team
from StaticAnalysis.analysis.Replay import get_side_replays
from StaticAnalysis.analysis.route_vis import plot_pregame_players
import matplotlib.pyplot as plt
from herotools.important_times import MAIN_TIME
from StaticAnalysis import session, team_session
from sqlalchemy.orm import Session
from pandas import DataFrame, read_sql
from StaticAnalysis.lib.Common import get_player_name, get_player_name_simple
from StaticAnalysis.replays.Player import Kills, Deaths
from StaticAnalysis.replays.Rune import Rune, RuneID


r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = session.query(Replay).filter(r_filter)
team: TeamInfo = get_team(8599101)
d_replays, r_replays = get_side_replays(r_query, session, team)
d_replays = d_replays.order_by(Replay.replayID.desc())
r_replays = r_replays.order_by(Replay.replayID.desc())

fig = plt.figure(figsize=(7, 7))

plot_pregame_players(d_replays[0], team, Team.DIRE, session, team_session, fig)
fig.tight_layout()
fig.savefig('pregame_route_dire.png')
fig.clf()
plot_pregame_players(r_replays[0], team, Team.RADIANT, session, team_session, fig)
fig.tight_layout()
fig.savefig('pregame_route_radiant.png')
fig.clf()

print(f"Dire ID: {d_replays[2].replayID} Radiant ID: {r_replays[2].replayID}")


def make_summary(
    replay: Replay, session: Session,
    min_time: int = None, max_time: int = None,
    bounty_grace: int = 30) -> dict:
    team_map = {p.steamID:p.team for p in replay.players}
    kills = {Team.DIRE: 0, Team.RADIANT: 0}
    deaths = {Team.DIRE: 0, Team.RADIANT: 0}
    bounties = {Team.DIRE: 0, Team.RADIANT: 0}
    first_blood = {Team.DIRE: 'no', Team.RADIANT: 'no'}
    
    # Setup the time filters
    if min_time is not None and max_time is not None:
        k_time = Kills.game_time.between(min_time, max_time)
        d_time = Deaths.game_time.between(min_time, max_time)
        r_time = Rune.game_time.between(min_time, max_time + bounty_grace)
    elif max_time is not None:
        k_time = Kills.game_time <= max_time
        d_time = Deaths.game_time <= max_time
        r_time = Rune.game_time <= max_time  + bounty_grace
    elif min_time is not None:
        k_time = Kills.game_time >= min_time
        d_time = Deaths.game_time >= min_time
        r_time = Rune.game_time >= min_time
    else:
        print(min_time, max_time)
        raise ValueError("One or both of min_time and max_time must be specified.")


    kill_query = session.query(Kills).filter(
        Kills.replay_ID == replay.replayID, k_time
    )
    kill: Kills
    is_first = True
    for kill in kill_query:
        if is_first:
            first_blood[team_map[kill.steam_ID]] = 'yes'
            is_first = False
        kills[team_map[kill.steam_ID]] += 1

    death_query = session.query(Deaths).filter(
        Deaths.replay_ID == replay.replayID, d_time
    )
    death: Deaths
    for death in death_query:
        deaths[team_map[death.steam_ID]] += 1

    rune_query = session.query(Rune).filter(
        Rune.replayID == replay.replayID, r_time,
        Rune.runeType == RuneID.Bounty
    )
    bounty: Rune
    for bounty in rune_query:
        bounties[bounty.team] += 1
        
    output = {
        Team.DIRE: f'''Kills: {kills[Team.DIRE]}, Deaths: {deaths[Team.DIRE]}, Bounties: {bounties[Team.DIRE]}, Drew First Blood: {first_blood[Team.DIRE]}''',
        Team.RADIANT: f'''Kills: {kills[Team.RADIANT]}, Deaths: {deaths[Team.RADIANT]}, Bounties: {bounties[Team.RADIANT]}, Drew First Blood: {first_blood[Team.RADIANT]}''',
    }
    
    return output


def get_summary_table(
    replay: Replay, session: Session, max_time: int, stat: type
    ) -> DataFrame:
    stat_query = session.query(stat.game_time, stat.steam_ID).filter(
        stat.replay_ID == replay.replayID, stat.game_time <= max_time)
    stat_df = read_sql(stat_query.statement, session.bind)
    
    # Add Player name
    name_mapper = lambda x: get_player_name_simple(x, team_session)
    stat_df['name'] = stat_df['steam_ID'].map(name_mapper)
    # Add playher team
    team_map = {p.steamID:p.team for p in replay.players}
    stat_df['team'] = stat_df['steam_ID'].map(team_map)
    
    return stat_df

kills_df = get_summary_table(d_replays[3], session, 10*60, Kills)
deaths_df = get_summary_table(d_replays[3], session, 10*60, Deaths)
summary = make_summary(d_replays[3], session, None, 0, 30)