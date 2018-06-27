from .Statistics import x_vs_time, xy_vs_time, cumulative_statistic
from pandas import DataFrame
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Replay import Replay, Team


def win_rate_table(session, team):

    def _process_replays(r_in, side):
        total = len(r_in)
        wins = 0

        for game in r_in:
            if side == game.winner:
                wins += 1

        return wins, total - wins

    output = DataFrame(columns=['Win', 'Losses'])

    f_dire = Replay.get_side_filter(team, Team.DIRE)
    r_dire = team.get_replays(session, f_dire).all()
    output.loc['Dire'] = _process_replays(r_dire, Team.DIRE)

    f_radiant = Replay.get_side_filter(team, Team.RADIANT)
    r_radiant = team.get_replays(session, f_radiant).all()
    output.loc['Radiant'] = _process_replays(r_radiant, Team.RADIANT)

    output.loc['All'] = output.loc['Dire'] + output.loc['Radiant']
    output['Rate'] = output['Win'] / (output['Win'] + output['Losses'])

    return output


def hero_win_rate(r_query, team):
    output = DataFrame(columns=['Win', 'Loss'])

    def _process(side):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        for r in replays:
            is_win = r.winner == side

            picks = [p.hero for t in r.teams if t.team == side for p in t.draft]

            for hero in picks:
                column = 'Win' if is_win else 'Loss'

                if hero in output[column]:
                    output.loc[hero, column] += 1
                else:
                    output.loc[hero, column] = 1

    _process(Team.DIRE)
    _process(Team.RADIANT)
    output.fillna(0, inplace=True)
    output['Total'] = output['Win'] + ['Loss']
    output['Rate'] = output['Win']/output['Total']

    return output
