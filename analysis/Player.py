from .Statistics import x_vs_time, xy_vs_time
from datetime import timedelta
from pandas import Series
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Player import Player
from replays.Replay import Replay


def cumulative_player(session, prop_name, team, filt):

    players = session.query(Player).filter(filt)\
                                   .join(Replay).filter(team.filter)
    # print(players)
    output = Series()

    for p in players:
        off_set_time = p.replay.gameStart
        for prop in getattr(p, prop_name):
            time = timedelta(seconds=(prop.time - off_set_time))
            if time in output:
                output[time] += prop.increment
            else:
                output[time] = prop.increment

    return output
