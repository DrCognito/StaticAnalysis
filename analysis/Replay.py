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

