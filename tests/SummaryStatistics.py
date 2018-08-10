import Setup
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.Replay import win_rate_table
from analysis.Player import cumulative_player, player_heroes, pick_context, player_position
from analysis.Replay import hero_win_rate, get_ptbase_tslice, pair_rate, get_smoke
from analysis.Replay import draft_summary
from replays.Replay import Replay, determine_side_byteam
from replays.Player import Player
from replays.TeamSelections import TeamSelections
from replays.Ward import Ward, WardType
from replays.Rune import Rune, RuneID
from replays.Scan import Scan
from lib.team_info import InitTeamDB, TeamInfo
from sqlalchemy.orm import sessionmaker

s_maker = Setup.get_testDB()
#session = s_maker()
session = Setup.get_fullDB()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()

team_test_id = 1375614
Teams = {
    'Mad Lads': team_session.query(TeamInfo)
                            .filter(TeamInfo.name == 'Fnatic').one()
}
# Teams = {
#     'Mad Lads': team_session.query(TeamInfo)
#                             .filter(TeamInfo.team_id == 5229049).one()
# }

team_test_id = 1375614
#team_test_id = 1375614

filt = (Replay.teams.any(TeamSelections.teamID == team_test_id), )


#Synderen
p_filter = (Player.steamID == 76561198047004422)


def test_cummulative_stat(stat='last_hits'):
    return cumulative_player(session, stat, Teams['Mad Lads'], p_filter)


def test_player_picks():
    return player_heroes(session, Teams['Mad Lads'], summarise=10)


r_query = Teams['Mad Lads'].get_replays(session)


def test_pick_context(hero='npc_dota_hero_beastmaster'):
    return pick_context(hero, Teams['Mad Lads'],
                        r_query)


def test_hero_winrate():
    return hero_win_rate(r_query, Teams['Mad Lads'])


def test_wards():
    return get_ptbase_tslice(session, r_query, team=Teams['Mad Lads'],
                             Type=Ward,
                             start=-2*60, end=10*60)


def test_scans():
    return get_ptbase_tslice(session, r_query, team=Teams['Mad Lads'],
                             Type=Scan,
                             start=-2*60, end=10*60)


def test_runes():
    return get_ptbase_tslice(session, r_query, team=Teams['Mad Lads'],
                             Type=Rune,
                             start=-2*60, end=10*60)


def test_pairs():
    return pair_rate(session, r_query, Teams['Mad Lads'])


def test_smokes():
    return get_smoke(r_query, session, Teams['Mad Lads'])


def test_player_position():
    return player_position(session, r_query, Teams['Mad Lads'],
                           player_slot=4,
                           start=-2*60, end=10*60)


def test_draft_summary():
    return draft_summary(session, r_query, Teams['Mad Lads'])


if __name__ == '__main__':
    win_rate = win_rate_table(r_query, Teams['Mad Lads'])
    print(win_rate)
    win_rate = win_rate[['First Rate', 'Second Rate', 'All Rate']]
    win_rate = win_rate.fillna(0)
    win_rate = win_rate.round(2)
    print(win_rate)
    last_hits = test_cummulative_stat()
    player_picks = test_player_picks()
    pick_context = test_pick_context()
    hero_winrate = test_hero_winrate()
    wards = test_wards()
    scans = test_scans()
    runes = test_runes()
    pairs = test_pairs()
    smokes = test_smokes()
    p5_position = test_player_position()
    draft_summary = test_draft_summary()