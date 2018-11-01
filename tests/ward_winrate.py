import Setup
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Ward import Ward, WardType
from replays.Replay import Team
from pandas import DataFrame, cut, read_sql, IntervalIndex, Interval, interval_range
from matplotlib import pyplot as plt
from os import environ as environment
import matplotlib.image as mpimg
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import MaxNLocator
from matplotlib import ticker

session = Setup.get_fullDB()

test = session.query(Ward.game_time, Ward.xCoordinate, Ward.yCoordinate,
                     Ward.winner)\
              .filter(Ward.team == Team.DIRE, Ward.ward_type == WardType.OBSERVER)

dire_df = read_sql(test.statement, session.bind)

#t_binning = [0, 10*60, 20*60, 30*60, 400*60]
t_binning = [(0, 10*60), (10*60, 20*60), (20*60, 30*60),
             (30*60, 400*60)]
#t_binning = interval_range(0, 30*60, 3)
t_binning = IntervalIndex.from_tuples(t_binning)
bins = 16
s_binning = [float(x)/bins for x in range(bins)]

dire_df['tbin'] = IntervalIndex(cut(dire_df['game_time'], t_binning, right=True))
dire_df['xbin'] = IntervalIndex(cut(dire_df['xCoordinate'], s_binning)).mid
dire_df['ybin'] = IntervalIndex(cut(dire_df['yCoordinate'], s_binning)).mid

dire_count = dire_df.groupby(['tbin', 'xbin', 'ybin'])[["winner"]].count()
dire_count = dire_count.reset_index()
dire_sum = dire_df.groupby(['tbin', 'xbin', 'ybin'])[["winner"]].sum()
dire_sum = dire_sum.reset_index()
dire_mean = dire_df.groupby(['tbin', 'xbin', 'ybin'])[["winner"]].mean()
dire_mean = dire_mean.reset_index()

summary = DataFrame({
    'x': dire_count['xbin'],
    'y': dire_count['ybin'],
    't': dire_count['tbin'],
    'mean': dire_mean['winner'],
    'wins': dire_sum['winner'],
    'total': dire_count['winner']
})

dire_mean.loc[dire_mean['tbin'] == Interval(0,600)].plot.hexbin(x='xbin', y='ybin', C='winner', gridsize=16)
dire_sum.loc[dire_sum['tbin'] == Interval(0,600)].plot.hexbin(x='xbin', y='ybin', C='winner', gridsize=16)


def plot_wards(query_data: DataFrame, weights: str, bins=16,
               ax_in=None):
    if ax_in is None:
        fig, ax_in = plt.subplots(figsize=(10, 10))
    else:
        fig = plt.gcf()

    plot = ax_in.hexbin(x=query_data['x'],
                        y=query_data['y'],
                        C=query_data[weights],
                        gridsize=bins, 
                        #mincnt=1,
                        #extent=[0, 1, 0, 1],
                        cmap='cool',
                        zorder=2)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')

    # Reposition colourbar
    # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
    divider = make_axes_locatable(ax_in)
    side_bar = divider.append_axes("right", size="5%", pad=0.05)
    cbar = plt.colorbar(plot, cax=side_bar)
    cbar.locator = ticker.MaxNLocator(integer=True)
    cbar.update_ticks()
    cbar.ax.tick_params(labelsize=14)

    return fig, ax_in

plot_wards(summary.loc[(summary['t'] == Interval(0,600)) & (summary['total'] > 10)], 'mean')
plot_wards(summary.loc[(summary['t'] == Interval(0,600)) & (summary['total'] > 10)], 'wins')
# plot_wards(summary.loc[summary['t'] == Interval(0,600)], 'total')

def make_summary(query_data, weights='mean'):
    fig, axList = plt.subplots(2,2, figsize=(8,10))

    data_in = summary.loc[(summary['t'] == t_binning[0]) & (summary['total'] > 10)]
    _, ax = plot_wards(data_in, weights=weights, ax_in=axList[0,0])
    ax.set_title("0 to 10min")

    data_in = summary.loc[(summary['t'] == t_binning[1]) & (summary['total'] > 10)]
    _, ax = plot_wards(data_in, weights=weights, ax_in=axList[0,1])
    ax.set_title("10 to 20min")

    data_in = summary.loc[(summary['t'] == t_binning[2]) & (summary['total'] > 10)]
    _, ax = plot_wards(data_in, weights=weights, ax_in=axList[1,0])
    ax.set_title("20 to 30min")

    data_in = summary.loc[(summary['t'] == t_binning[3]) & (summary['total'] > 10)]
    _, ax = plot_wards(data_in, weights=weights, ax_in=axList[1,1])
    ax.set_title("30+mins")

    return fig, axList


fig, ax = make_summary(summary)
fig.tight_layout()
fig.savefig("ward_rate.png")