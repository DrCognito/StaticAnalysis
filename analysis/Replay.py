from .Statistics import x_vs_time, xy_vs_time, cumulative_statistic
from pandas import DataFrame
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Replay import Replay, Team


def win_rate_table(session, filt, team_select):

    def _process_replays(r_in):
        total = len(r_in)
        wins = 0

        for game in r_in:
            team = team_select(game)
            if team == game.winner:
                wins += 1

        return wins, total - wins, wins/total

    output = DataFrame(columns=['Win', 'Losses', 'Rate'])

    replays = list(session.query(Replay).filter(*filt))
    output.loc['All'] = _process_replays(replays)

    def _team_pred(r, t):
        print(r,t)
        return team_select(r) == t

    dire = session.query(Replay).filter(*filt)
    dire = list(filter(lambda x: team_select(x) == Team.DIRE, dire))
    output.loc['Dire'] = _process_replays(dire)

    radiant = session.query(Replay).filter(*filt)
    radiant = list(filter(lambda x: team_select(x) == Team.RADIANT, radiant))
    output.loc['Radiant'] = _process_replays(radiant)

    return output

