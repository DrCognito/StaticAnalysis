from pandas import DataFrame, cut
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.team_info import TeamInfo
from analysis.Player import PlayerStatus
from analysis.Replay import Replay

def get_binned_df_xy(df: DataFrame, bins=64, min_percentile=0.7):
    binning = [float(x)/bins for x in range(bins)]
    df['xBin'] = cut(df['xCoordinate'], binning)
    df['yBin'] = cut(df['yCoordinate'], binning)

    weightSeries = df.groupby(['xBin', 'yBin']).size()
    flat_index = weightSeries.reset_index()
    if min_percentile is not None:
        q1 = weightSeries.quantile(min_percentile)
        flat_index = flat_index[flat_index[0] > q1]

    return flat_index
