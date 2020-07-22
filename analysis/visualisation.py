from os import environ as environment

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.axes import Axes
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas import DataFrame, Series, cut, read_sql
from PIL import Image
from lib.team_info import TeamInfo

from lib.HeroTools import HeroIconPrefix, HeroIDType, convertName, heroShortName
from .Player import pick_context

import copy
colour_list = ['cool', 'summer', 'winter', 'spring', 'copper']


def plot_map_points(query, bins=128):
    coordinates = ((q.xCoordinate, q.yCoordinate) for q in query)

    x, y = zip(*coordinates)
    heatmap, xedges, yedges = np.histogram2d(x, y, bins=bins,
                                             range=[[0, 1], [0, 1]],
                                             normed=False)

    return heatmap, xedges, yedges


def dataframe_xy_time_smoke(query, Type, session):
    sql_query = query.with_entities(Type.averageXCoordinateStart.label('xCoordinate'),
                                    Type.averageYCoordinateStart.label('yCoordinate'),
                                    Type.game_start_time).statement

    data = read_sql(sql_query, session.bind)

    return data


def dataframe_xy_time(query, Type, session):
    sql_query = query.with_entities(Type.xCoordinate,
                                    Type.yCoordinate,
                                    Type.game_time).statement

    data = read_sql(sql_query, session.bind)

    return data


def dataframe_xy(query, Type, session):
    sql_query = query.with_entities(Type.xCoordinate,
                                    Type.yCoordinate).statement

    data = read_sql(sql_query, session.bind)

    return data


def make_image_annotation(icon, axes, x, y, size=1.0):
    icon = Image.open(icon)
    # Resize if necessary
    if size != 1.0:
        width, height = icon.size
        width = width*size
        height = height*size
        icon.thumbnail((width, height))

    imagebox = OffsetImage(icon)
    imagebox.image.axes = axes

    ab = AnnotationBbox(imagebox, (x, y),
                        xycoords='axes fraction',
                        boxcoords="offset points",
                        pad=0,
                        frameon=False
                        )

    axes.add_artist(ab)

    return imagebox


def make_image_annotation2(image, axes, x, y, size=1.0, bbox=None):
    # mage = Image.open(image)
    # Resize if necessary
    if size != 1.0:
        width, height = image.size
        width = width*size
        height = height*size
        image.thumbnail((width, height))

    imagebox = OffsetImage(image)
    imagebox.image.axes = axes

    ab = AnnotationBbox(imagebox, (x, y),
                        xycoords='axes fraction',
                        boxcoords="offset points",
                        pad=0,
                        frameon=False,
                        box_alignment=(0.5, 0)
                        )

    axes.add_artist(ab)

    return imagebox


def x_label_icon(axis, y_pos=-0.15, size=1.0):
    x_axis = axis.get_xaxis()

    x_labels = x_axis.get_majorticklabels()
    x_locations = x_axis.get_major_locator()

    x_min, x_max = axis.get_xlim()
    x_range = x_max - x_min

    extra_artists = []
    for label, x_loc in zip(x_labels, x_locations.locs):
        # This position wont work for some plots
        # x, _ = label.get_position()
        x = x_loc
        hero = label.get_text()
        try:
            # Get and resize the hero icon.
            icon = HeroIconPrefix / convertName(hero, HeroIDType.NPC_NAME,
                                                HeroIDType.ICON_FILENAME)
        except ValueError:
            print("Unable to find hero icon for: " + hero)
            continue
        x_rel = (float(x) - x_min)/x_range
        artist = make_image_annotation(icon, axis, x_rel, y_pos, size)
        extra_artists.append(artist)

    # Remove the old xlabels
    axis.set_xticklabels([])
    return extra_artists


def plot_player_heroes(data: DataFrame):

    figure, axes = plt.subplots(5)
    figure.set_size_inches(6, 10)

    def _plot_player(column: Series, name: str, axis, colour: str):
        # This filters out zeroes in a series
        # column = column.iloc[column.nonzero()]
        column = column.iloc[column.to_numpy().nonzero()]
        if column.empty:
            axis.text(0.5, 0.5, "No Data", fontsize=14,
                      horizontalalignment='center',
                      verticalalignment='center')
            axis.set_ylabel(name)
            axis.yaxis.set_major_locator(MaxNLocator(integer=True))
            return axis, []
        column.sort_values(ascending=False, inplace=True)
        ax: Axes = column.plot.bar(ax=axis, sharey=True, colormap=colour)
        ax.set_ylabel(name)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        extra_artists = x_label_icon(ax, y_pos=-0.2, size=0.8)

        return ax, extra_artists

    extra_artists = []
    for i_ax, player in enumerate(data.columns):
        ax, extra = _plot_player(data[player], player, axes[i_ax], colour=colour_list[i_ax])
        extra_artists += extra

    return figure, extra_artists


def plot_draft_summary(picks: DataFrame, bans: DataFrame):
    '''Plot an abbreviated pick and ban count for a team.
       Stages will be combined.
    '''
    fig, axes = plt.subplots(2, 3, sharey='row')
    fig.set_size_inches(8, 7)
    pick_colour = colour_list[0]
    ban_colour = colour_list[1]
    extra_artists = []

    def _combine_results(data: DataFrame, columns):
        return data.iloc[:, columns[0]:columns[1]].sum(axis=1)\
                   .sort_values(ascending=False)
    # Picks
    pick_stage = []
    pick_stage.append(_combine_results(picks, (0, 2)))
    pick_stage.append(_combine_results(picks, (2, 4)))
    pick_stage.append(_combine_results(picks, (4, None)))

    for i, i_ax in enumerate(axes[0]):
        if pick_stage[i][0:5].empty:
            i_ax.text(0.5, 0.5, "No Data", fontsize=14,
                      horizontalalignment='center',
                      verticalalignment='center')
            i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            continue
        pick_stage[i][0:5].plot.bar(ax=i_ax, legend=False, width=0.9,
                                    colormap=pick_colour, grid=True,
                                    fontsize=8, sharey=True)
        extra_artists += x_label_icon(i_ax, y_pos=-0.1, size=0.8)

    # Bans
    ban_stage = []
    ban_stage.append(_combine_results(bans, (0, 3)))
    ban_stage.append(_combine_results(bans, (3, 5)))
    ban_stage.append(_combine_results(bans, (5, None)))

    for i, i_ax in enumerate(axes[1]):
        if ban_stage[i][0:5].empty:
            i_ax.text(0.5, 0.5, "No Data", fontsize=14,
                      horizontalalignment='center',
                      verticalalignment='center')
            i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            continue
        ban_stage[i][0:5].plot.bar(ax=i_ax, legend=False, width=0.9,
                                   colormap=ban_colour, grid=True,
                                   fontsize=8, sharey=True)
        extra_artists += x_label_icon(i_ax, y_pos=-0.1, size=0.8)
        i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    axes[0][0].set_ylabel('Picks', fontsize=18)
    axes[1][0].set_ylabel('Bans', fontsize=18)

    return fig, extra_artists


def plot_pick_pairs(data: DataFrame, num_heroes=10):
    '''Plots pick pair combinations for the DataFrame data.
       Heroes are replaced by icons.
       num_heroes determines the number of paris to consider.
       Returns axis and extra artists for extending bounding box.
    '''
    working = data[:num_heroes]
    fig, axis = plt.subplots()

    if working.empty:
        axis.text(0.5, 0.5, "No Data", fontsize=14,
                  horizontalalignment='center',
                  verticalalignment='center')
        axis.yaxis.set_major_locator(MaxNLocator(integer=True))
        return fig, []

    working.plot.bar(ax=axis, width=0.9, grid=True)
    axis.yaxis.set_major_locator(MaxNLocator(integer=True))

    hero_pairs = (h.split(', ') for h in working.index)

    x_axis = axis.get_xaxis()
    x_locations = x_axis.get_major_locator()

    x_min, x_max = axis.get_xlim()
    x_range = x_max - x_min

    extra_artists = []

    for h_pair, x_loc in zip(hero_pairs, x_locations.locs):
        try:
            i1 = HeroIconPrefix / convertName(h_pair[0], HeroIDType.NPC_NAME,
                                              HeroIDType.ICON_FILENAME)
        except ValueError:
            print("Unable to find hero icon for: " + hero)
            continue
        try:
            i2 = HeroIconPrefix / convertName(h_pair[1], HeroIDType.NPC_NAME,
                                              HeroIDType.ICON_FILENAME)
        except ValueError:
            print("Unable to find hero icon for: " + hero)
            continue

        y_pos1 = -0.1
        y_pos2 = -0.22
        size = 1.0

        x_rel = (float(x_loc) - x_min)/x_range
        a1 = make_image_annotation(i1, axis, x_rel, y_pos1, size)
        a2 = make_image_annotation(i2, axis, x_rel, y_pos2, size)
        # Should only need the bottom artist
        extra_artists.append(a2)

    axis.set_xticklabels([])
    axis.yaxis.set_major_locator(MaxNLocator(integer=True))

    return fig, extra_artists


def plot_pick_context(picks: DataFrame, team, r_query, summarise=False):
    '''Plots the context (in picks and bans) of a teams top picks.
       Input is a DataFrame of picks, the TeamInfo and r_query
       context.
    '''
    top_picks = picks.sum(axis=1).sort_values(ascending=False)
    fig, axes = plt.subplots(4, 5, sharey='row')
    fig.set_size_inches(8,9)

    extra_artists = []

    def _do_plot(axis, colour, data):
        data.plot.bar(ax=axis, width=0.9,
                      colormap=colour, grid=True,
                      fontsize=8, sharey=True)
        extra_artists = x_label_icon(axis, y_pos=-0.15, size=0.5)
        axis.yaxis.set_major_locator(MaxNLocator(integer=True))

        return extra_artists

    def _summarise(table, after: int):
        '''Assumes table is already sorted descending.'''
        other = table[after:].sum()
        table['Other'] = other
        table.sort_values(ascending=False, inplace=True)
        return table[:after + 1]

    for i_pick, pick in enumerate(top_picks[:5].index):
        nick = convertName(pick, HeroIDType.NPC_NAME,
                           HeroIDType.NICK_NAME)
        axes[0, i_pick].set_title(nick)

        context = pick_context(pick, team, r_query)
        pick = context['Pick'].sort_values(ascending=False)
        pick = _summarise(pick, 5) if summarise else pick[:5]

        ban = context['Ban'].sort_values(ascending=False)
        ban = _summarise(ban, 5) if summarise else ban[:5]

        opick = context['Opponent Pick'].sort_values(ascending=False)
        opick = _summarise(opick, 5) if summarise else opick[:5]

        oban = context['Opponent Ban'].sort_values(ascending=False)
        oban = _summarise(oban, 5) if summarise else oban[:5]

        _do_plot(axes[0, i_pick], colour_list[0], pick)
        _do_plot(axes[1, i_pick], colour_list[1], ban)
        _do_plot(axes[2, i_pick], colour_list[2], opick)
        a4 = _do_plot(axes[3, i_pick], colour_list[3], oban)
        extra_artists += a4

    axes[0, 0].set_ylabel('Pick', fontsize=14)
    axes[1, 0].set_ylabel('Ban', fontsize=14)
    axes[2, 0].set_ylabel('Opponent Pick', fontsize=14)
    axes[3, 0].set_ylabel('Opponent Ban', fontsize=14)

    return fig, axes, extra_artists


def get_binning_percentile_xy(df: DataFrame, bins=64, percentile=(0.7,0.999)):
    binning = [float(x)/bins for x in range(bins)]
    df['xBin'] = cut(df['xCoordinate'], binning)
    df['yBin'] = cut(df['yCoordinate'], binning)

    weightSeries = df.groupby(['xBin', 'yBin']).size()

    return weightSeries.quantile(percentile[0]),\
           weightSeries.quantile(percentile[1])


def get_binning_max_xy(df: DataFrame, bins=64):
    binning = [float(x)/bins for x in range(bins)]
    working_df = DataFrame()
    working_df['xBin'] = cut(df['xCoordinate'], binning)
    working_df['yBin'] = cut(df['yCoordinate'], binning)

    weightSeries = working_df.groupby(['xBin', 'yBin']).size()

    return weightSeries.max()


def plot_player_positioning(query_data: DataFrame):
    fig, ax_in = plt.subplots(figsize=(10, 10))
    # jet = plt.get_cmap('afmhot')
    colour_map = copy.copy(plt.get_cmap('afmhot'))
    colour_map.set_under('black', alpha=0.0)

    vmin, vmax = get_binning_percentile_xy(query_data)
    # plot = query_data.plot.hexbin(x='xCoordinate', y='yCoordinate',
    #                               gridsize=64, mincnt=1,
    #                               vmin=vmin, vmax=vmax,
    #                               extent=[0, 1, 0, 1],
    #                               #interpolation='none'
    #                               colormap=jet,
    #                               ax=ax1, zorder=2)

    plot = ax_in.hexbin(x=query_data['xCoordinate'],
                        y=query_data['yCoordinate'],
                        gridsize=64, mincnt=1,
                        vmin=vmin, vmax=vmax,
                        extent=[0, 1, 0, 1],
                        cmap=colour_map,
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


def plot_object_position(query_data: DataFrame, bins=64,
                         ax_in=None, vmin=None, vmax=None):
    if ax_in is None:
        fig, ax_in = plt.subplots(figsize=(10, 10))
    else:
        fig = plt.gcf()

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)
    if vmax is None:
        vmax = get_binning_max_xy(query_data, bins)
        if vmax == 1:
            vmax = 2

    if not query_data.empty:
        plot = ax_in.hexbin(x=query_data['xCoordinate'],
                            y=query_data['yCoordinate'],
                            gridsize=bins, mincnt=0,
                            extent=[0, 1, 0, 1],
                            cmap=colour_map,
                            vmin=1, vmax=vmax + 0.5,
                            zorder=2)
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot, cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')

    return fig, ax_in


def plot_hero_winrates(data: DataFrame, mingames=3, min_rate=0.6):
    '''Plots hero win rate over all and with a minimum games required.'''

    fig, axes = plt.subplots(2, figsize=(10, 10))
    data.rename(heroShortName, inplace=True)

    def _do_plot(ax_in, data):
        sub_set: DataFrame = data.loc[data['Rate'] >= min_rate]\
            .sort_values(['Rate', 'Total'], ascending=False,)

        if sub_set.empty:
            ax_in.text(0.5, 0.5, "No Data", fontsize=14,
                       horizontalalignment='center',
                       verticalalignment='center')
            ax_in.yaxis.set_major_locator(MaxNLocator(integer=True))
            return
        bar_plot = sub_set['Rate'].plot.bar(ax=ax_in)

        for bar, label in zip(bar_plot.patches, sub_set['Total'].iteritems()):
            y = bar.get_height()
            x = bar.get_x() + bar.get_width() / 2
            ax_in.text(s=int(label[1]), x=x, y=y,
                       ha='center', va='bottom',
                       color='black')
        ax_in.set_ylim([max(min_rate - 0.1, 0), None])

    _do_plot(axes[0], data)

    subset = data.loc[data['Total'] > mingames]
    if not subset.empty:
        _do_plot(axes[1], subset)

    axes[0].set_ylabel('All')
    axes[1].set_ylabel('Min {} games'.format(mingames))

    return fig, axes


def plot_object_position_scatter(query_data: DataFrame, size=700, ax_in=None):
    if ax_in is None:
        fig, ax_in = plt.subplots(figsize=(10, 10))

    colour_map = copy.copy(plt.get_cmap('afmhot'))
    colour_map.set_under('black', alpha=0.0)

    plot = ax_in.scatter(x=query_data['xCoordinate'],
                         y=query_data['yCoordinate'],
                         c=query_data['game_time'],
                         s=size,
                        #  extent=[0, 1, 0, 1],
                         cmap='autumn_r',
                         alpha=0.5,
                         zorder=2)
    ax_in.set_xlim(0, 1)
    ax_in.set_ylim(0, 1)

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

    return plot


def plot_runes(rune_data: DataFrame, team: TeamInfo):
    fig, axes = plt.subplots(2, figsize=(10, 10))

    bounty = rune_data[['Team Bounty', 'Opposition Bounty']]
    power = rune_data[['Team Power', 'Opposition Power']]

    def _process_runes(data: DataFrame, axis, labels):
        data[labels[0]] = data.iloc[:, 0]/(data.iloc[:, 0] + data.iloc[:, 1])
        data[labels[1]] = data.iloc[:, 1]/(data.iloc[:, 0] + data.iloc[:, 1])

        data[[*labels]].plot.bar(stacked=True, ax=axis)
        xmin, xmax = axis.get_xlim()
        axis.plot((xmin, xmax), (0.5, 0.5), linewidth=3, color='r')

    power = power.resample('2T').sum()[1:11]
    _process_runes(power, axes[0], [team.name, "Opposition"])
    axes[0].set_ylabel("Power", fontsize=14)

    bounty = bounty.resample('5T').sum()[:10]
    _process_runes(bounty, axes[1], [team.name, "Opposition"])
    axes[1].set_ylabel("Bounty", fontsize=14)

    def _add_t_labels(ax_in, mins_per_tick: int, off_set=0):
        time_slices = len(ax_in.get_xticklabels())
        labels = []
        for x in range(time_slices):
            t1 = x*mins_per_tick + off_set
            t2 = (x+1)*mins_per_tick + off_set
            labels.append("{} to {} min".format(t1, t2))
        ax_in.set_xticklabels(labels)
        ax_in.legend_.remove()

    _add_t_labels(axes[0], 2, off_set=2)
    _add_t_labels(axes[1], 5)

    return fig, axes
