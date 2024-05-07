from matplotlib.collections import PolyCollection
from StaticAnalysis.snippets.minimal_db import session, team_session, team
from StaticAnalysis.replays.Replay import Replay
from herotools.important_times import MAIN_TIME
from StaticAnalysis.analysis.Player import player_position, PlayerStatus
from StaticAnalysis.analysis.visualisation import dataframe_xy, get_binning_percentile_xy, plot_object_position
import matplotlib.pyplot as plt
from pandas import DataFrame, cut
from StaticAnalysis.lib.Common import EXTENT

r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = team.get_replays(session).filter(r_filter)
position = 0 # Choses the player in team
recent_limit = 5
start = -2*60
end = 10*60

((pos_dire, pos_dire_limited),
(pos_radiant, pos_radiant_limited)) = player_position(
                                                      session,
                                                      r_query,
                                                      team,
                                                      player_slot=position,
                                                      start=start, end=end,
                                                      recent_limit=recent_limit)
# Normal method
pos_dire_df = dataframe_xy(pos_dire, PlayerStatus, session)
pos_dire_limited_df = dataframe_xy(pos_dire_limited, PlayerStatus, session)

fig, axes = plt.subplots(1, 2, figsize=(15, 10))

# vmin, vmax = get_binning_percentile_xy(pos_dire_df)
# vmin = max(1.0, vmin)
# axis = plot_object_position(pos_dire_df,
#                             bins=64, fig_in=fig, ax_in=axes[0],
#                             vmin=vmin, vmax=vmax)

# vmin, vmax = get_binning_percentile_xy(pos_dire_limited_df)
# vmin = max(1.0, vmin)
# axis = plot_object_position(pos_dire_limited_df,
#                             bins=64, fig_in=fig, ax_in=axes[1],
#                             vmin=vmin, vmax=vmax)
# axis.set_title('Latest 5 games')

# fig.tight_layout()
# fig.savefig("timado_pos_default.png", bbox_inches='tight')

def bin_pos_data(df: DataFrame, bins=64, extent=EXTENT):
    binning = [float(x) / bins for x in range(bins)]

    xExtent = float(abs(extent[1] - extent[0]))
    xBins = [extent[0] + x * xExtent for x in binning]

    yExtent = float(abs(extent[3] - extent[2]))
    yBins = [extent[2] + y * yExtent for y in binning]

    # with ChainedAssignment():
    df['xBin'] = cut(df['xCoordinate'], xBins)
    df['yBin'] = cut(df['yCoordinate'], yBins)

    df = df.groupby(['xBin', 'yBin'], observed=True, as_index=False)[['xCoordinate']].count()
    df['xBin'] = df['xBin'].apply(lambda x: x.mid)
    df['yBin'] = df['yBin'].apply(lambda x: x.mid)

    return df

import copy
from os import environ as environment
import matplotlib.image as mpimg
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import ticker
def plot_counts_hexbin(query_data: DataFrame, bins=64,
                fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = ax_in.hexbin(x=query_data['xBin'],
                            y=query_data['yBin'],
                            C=query_data['xCoordinate'],
                            gridsize=bins, mincnt=0,
                            extent=EXTENT,
                            cmap=colour_map,
                            vmin=vmin, vmax=vmax,
                            zorder=2)
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot, cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in


def get_hexbin_binning(pollies: PolyCollection):
    pass

def plot_counts_hist2d(query_data: DataFrame, bins=64,
                fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        # plot = ax_in.hexbin(x=query_data['xBin'],
        #                     y=query_data['yBin'],
        #                     C=query_data['xCoordinate'],
        #                     gridsize=bins, mincnt=0,
        #                     extent=EXTENT,
        #                     cmap=colour_map,
        #                     vmin=vmin, vmax=vmax,
        #                     zorder=2)
        plot = ax_in.hist2d(x=query_data['xBin'],
                            y=query_data['yBin'],
                            weights=query_data['xCoordinate'],
                            bins=bins,
                            # extent=EXTENT,
                            range=[[EXTENT[0], EXTENT[1]], [EXTENT[2], EXTENT[3]]],
                            cmap=colour_map,
                            cmin=vmin, cmax=vmax,
                            zorder=2)
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot[3], cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in


def plot_counts_pcolormesh(
    query_data: DataFrame, bins=64,
    fig_in=None, ax_in=None,
    vmin=1):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    import numpy as np
    # [[xmin, xmax], [ymin, ymax]]
    extent_numpy = [[EXTENT[0], EXTENT[1]], [EXTENT[2], EXTENT[3]]]
    vals, xedges, yedges = np.histogram2d(
        x=query_data['xCoordinate'],
        y=query_data['yCoordinate'],
        bins=64,
        range=extent_numpy
    )
    X, Y = np.meshgrid(xedges, yedges)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = ax_in.pcolormesh(
            X,
            Y,
            vals.T,
            # extent=EXTENT,
            vmin=vmin,
            cmap=colour_map,
            zorder=2
            )
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot, cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in


import seaborn as sns
def plot_seaborn_kde(query_data: DataFrame, bins=64,
                fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = sns.kdeplot(
            data=query_data,
            # x=query_data['xBins'], y=query_data['yBins'],
            x=query_data['xBin'].astype(float), y=query_data['yBin'].astype(float),
            weights=query_data['xCoordinate'].astype(int),
            palette=colour_map,
            # extent=EXTENT,
            gridsize=64,
            cbar=True,
            ax=ax_in,
            levels=4,
            # thresh=1,
            fill=True
        )
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        # divider = make_axes_locatable(ax_in)
        # side_bar = divider.append_axes("right", size="5%", pad=0.05)
        # cbar = plt.colorbar(plot, cax=side_bar)
        # cbar.locator = ticker.MaxNLocator(integer=True)
        # cbar.update_ticks()
        # cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in

binned_dire = bin_pos_data(pos_dire_df)
vmin, vmax = binned_dire['xCoordinate'].quantile(0.7), binned_dire['xCoordinate'].quantile(0.999)
# axis = plot_counts_hist2d(binned_dire,
#                    bins=64, fig_in=fig, ax_in=axes[0],
#                    vmin=vmin, vmax=vmax)
# axis = plot_counts_pcolormesh(binned_dire,
#                    bins=64, fig_in=fig, ax_in=axes[0])

binned_dire_limited = bin_pos_data(pos_dire_limited_df)
vmin, vmax = binned_dire_limited['xCoordinate'].quantile(0.7), binned_dire_limited['xCoordinate'].quantile(0.999)
# axis = plot_counts_hist2d(binned_dire_limited,
#                    bins=64, fig_in=fig, ax_in=axes[1],
#                    vmin=vmin, vmax=vmax)
# axis = plot_counts_pcolormesh(binned_dire_limited,
#                    bins=64, fig_in=fig, ax_in=axes[1])
# axis.set_title('Latest 5 games')

# fig.tight_layout()
# fig.savefig("timado_pos_cached.png", bbox_inches='tight')

plot_counts_pcolormesh(pos_dire_df, fig_in=fig, ax_in=axes[0], vmin=vmin)
plot_counts_pcolormesh(pos_dire_limited_df, fig_in=fig, ax_in=axes[1], vmin=vmin)
axes[1].set_title('Latest 5 games')

fig.tight_layout()
fig.savefig("timado_pos_pmesh.png", bbox_inches='tight')