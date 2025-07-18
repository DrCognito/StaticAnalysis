import copy
from typing import Dict

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from herotools.HeroTools import (HeroIconPrefix, HeroIDType, convertName,
                                 heroShortName)
from matplotlib import ticker
from matplotlib import colormaps as mpl_colormaps
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas import DataFrame, Series, cut, read_sql
from PIL import Image

import StaticAnalysis
from StaticAnalysis.analysis.Player import pick_context
from StaticAnalysis.lib.Common import EXTENT, ChainedAssignment, colours
from StaticAnalysis.lib.team_info import TeamInfo
import matplotlib.patches as mpatches


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


def dataframe_xy(query, Type, session) -> DataFrame:
    sql_query = query.with_entities(Type.xCoordinate,
                                    Type.yCoordinate).statement

    data = read_sql(sql_query, session.bind)

    return data


def make_image_annotation(icon, axes, x, y, size=1.0):
    icon = Image.open(icon)
    icon = icon.convert("RGBA")
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


def make_image_annotation_table(icon, axes, x, y, size=1.0):
    icon = Image.open(icon)
    icon = icon.convert("RGBA")

    if size != 1.0:
        icon.thumbnail((size, size))

    imagebox = OffsetImage(icon)
    imagebox.image.axes = axes

    # ab = AnnotationBbox(imagebox, (x, y),
    #                     xycoords='data',
    #                     boxcoords="data",
    #                     pad=0,
    #                     frameon=True,
    #                     box_alignment=(0, 0)
    #                     )
    ab = AnnotationBbox(imagebox, (x, y),
                        # xycoords='data',
                        # boxcoords="data",
                        pad=0,
                        frameon=False,
                        box_alignment=(0, 1.0)
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


def make_image_annotation_flex(icon, axes, x, y, size=1.0, bbox=None):
    icon = Image.open(icon)
    icon = icon.convert("RGBA")
    if size != 1.0:
        width, height = icon.size
        width = width*size
        height = height*size
        icon.thumbnail((width, height))

    imagebox = OffsetImage(icon)
    imagebox.image.axes = axes

    ab = AnnotationBbox(imagebox, (x, y),
                        xycoords='data',
                        boxcoords="data",
                        pad=0,
                        frameon=False,
                        box_alignment=(1.15, 0.5)
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
        except (ValueError, KeyError):
            print("Unable to find hero icon for 1: " + hero)
            continue
        x_rel = (float(x) - x_min)/x_range
        artist = make_image_annotation(icon, axis, x_rel, y_pos, size)
        extra_artists.append(artist)

    # Remove the old xlabels
    axis.set_xticklabels([])
    return extra_artists


def plot_player_heroes(data: DataFrame, axes: list):

    # fig.set_size_inches(8, 11)
    # axes = fig.subplots(5)

    def _plot_player(column: Series, name: str, axis, colour: str):
        icon_size = 0.7
        # This filters out zeroes in a series
        # column = column.iloc[column.nonzero()]
        column = column.iloc[column.to_numpy().nonzero()]
        if column.empty:
            axis.text(0.5, 0.5, "No Data", fontsize=18,
                      horizontalalignment='center',
                      verticalalignment='center')
            axis.set_ylabel(name)
            axis.yaxis.set_ticks([])
            axis.xaxis.set_ticks([])
            return axis, []
        column.sort_values(ascending=False, inplace=True)
        ax: Axes = column.plot.bar(ax=axis, colormap=colour)
        ax.set_ylabel(name)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        extra_artists = x_label_icon(ax, y_pos=-0.1, size=icon_size)
        ax.xaxis.set_ticks([])

        return ax, extra_artists

    extra_artists = []
    for i_ax, player in enumerate(data.columns):
        ax, extra = _plot_player(data[player], player, axes[i_ax], colour=colour_list[i_ax])
        extra_artists += extra

    return extra_artists


def plot_flex_picks(data: DataFrame, fig: Figure):
    player_bars_x = {p: list() for p in data.columns}
    player_bars_y = {p: list() for p in data.columns}
    pcolours = {p:col for p, col in zip(data.columns, colours)}
    x_ticks = []
    x_labels = []

    hero_icons = {}
    b_width = 0.5
    set_gap = 2*b_width
    position = 0.0

    # iterrows tuple, [0] is index, [1] series for row
    for row in data.iterrows():
        row_pos = 0
        entries = 0

        # for player, count in row[1].iteritems():
        for player, count in [*row[1].items()][::-1]:
            if count == 0:
                continue
            player_bars_x[player].append(position)
            player_bars_y[player].append(count)
            row_pos += position

            x_ticks.append(position)
            x_labels.append(player)

            position += b_width
            entries += 1

        hero_icons[row[0]] = row_pos / entries

        # Add gap between heroes
        position += set_gap

    position -= set_gap
    fig.set_size_inches(6, max(0.5*position, 6))
    axe = fig.subplots()
 
    has_data = False
    for player in player_bars_x:
        if player_bars_x[player]:
            has_data = True
            axe.barh(player_bars_x[player], player_bars_y[player],
                     height=0.7*b_width, label=player, color=pcolours[player])
            axe.set_yticks(x_ticks, x_labels)
    axe.yaxis.set_tick_params(pad=33)

    # Custom legend
    handles = []
    for p in data.columns:
        patch = mpatches.Patch(facecolor=pcolours[p], label=p)
        handles.append(patch)

    axe.legend(
        handles = handles,
        )

    if not has_data:
        axe.text(0.5, 0.5, "No Data", fontsize=14,
                 horizontalalignment='center',
                 verticalalignment='center')

        return fig, []

    # Add heroes
    size = 0.9
    x_pos = 0.0
    extra_artists = []
    for hero in hero_icons:
        try:
            # Get and resize the hero icon.
            icon = HeroIconPrefix / convertName(hero, HeroIDType.NPC_NAME,
                                                HeroIDType.ICON_FILENAME)
        except (ValueError, KeyError):
            print("Unable to find hero icon for 2: " + hero)
            continue
        artist = make_image_annotation_flex(icon, axe, x_pos, hero_icons[hero], size)
        extra_artists.append(artist)
    axe.set_ylim([-1*set_gap, None])
    # axe.xaxis.set_major_formatter(FormatStrFormatter('%i'))
    axe.xaxis.set_major_locator(MaxNLocator(integer=True))
    axe.legend()
    axe2 = axe.twiny()
    axe2.set_xticks(axe.get_xticks())
    axe2.set_xbound(axe.get_xbound())
    axe2.xaxis.set_major_locator(MaxNLocator(integer=True))
    # axe2.xaxis.set_major_formatter(FormatStrFormatter('%i'))
    # fig.subplots_adjust(left=0.2)

    return fig, extra_artists


def plot_draft_summary(picks: DataFrame, bans: DataFrame, fig: Figure):
    '''Plot an abbreviated pick and ban count for a team.
       Stages will be combined.
    '''
    fig.set_size_inches(8.27, 11.69*0.6)

    pick_ratios = [1, 2, 1]
    ban_ratios = [2, 1, 1]

    axes = fig.subplots(3, 2)
    picks_ax, bans_ax = zip(*axes)
    pick_colour = colour_list[0]
    ban_colour = colour_list[1]
    extra_artists = []

    def _combine_results(data: DataFrame, columns):
        data = data[data.columns.intersection(columns)].sum(axis=1).sort_values(ascending=False)
        return data[data > 0]
    # Picks
    pick_stage = []
    pick_stage.append(_combine_results(picks, [8, 9]))  # pick 1
    pick_stage.append(_combine_results(picks, [13, 14, 15, 16, 17, 18]))  # pick 2, 3, 4
    pick_stage.append(_combine_results(picks, [23, 24]))  # pick 5

    for p, i_ax, r in zip(pick_stage, picks_ax, pick_ratios):
        if p[0:10].empty:
            i_ax.text(0.5, 0.5, "No Data", fontsize=14,
                      horizontalalignment='center',
                      verticalalignment='center')
            i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            continue
        p[0:10].plot.bar(ax=i_ax, legend=False, width=0.9,
                         colormap=pick_colour, grid=True,
                         fontsize=8)
        extra_artists += x_label_icon(i_ax, y_pos=-0.12, size=0.65)
        i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Bans
    ban_stage = []
    ban_stage.append(_combine_results(bans, [1, 2, 3, 4, 5, 6, 7]))
    ban_stage.append(_combine_results(bans, [10, 11, 12]))
    ban_stage.append(_combine_results(bans, [19, 20, 21, 22]))

    for b, i_ax, r in zip(ban_stage, bans_ax, ban_ratios):
        if b[0:10].empty:
            i_ax.text(0.5, 0.5, "No Data", fontsize=14,
                      horizontalalignment='center',
                      verticalalignment='center')
            i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            continue
        b[0:10].plot.bar(ax=i_ax, legend=False, width=0.9,
                         colormap=ban_colour, grid=True,
                         fontsize=8)
        extra_artists += x_label_icon(i_ax, y_pos=-0.12, size=0.65)
        i_ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    picks_ax[0].set_ylabel('First Phase', fontsize=15)
    picks_ax[1].set_ylabel('Second Phase', fontsize=15)
    picks_ax[2].set_ylabel('Third Phase', fontsize=15)
    picks_ax[0].set_title('Picks', fontsize=15)
    bans_ax[0].set_title('Bans', fontsize=15)


    return fig, extra_artists


def plot_pick_pairs(data: Dict[int, DataFrame], fig: Figure, num_heroes=10):
    '''Plots pick pair combinations for the DataFrame data.
       Heroes are replaced by icons.
       num_heroes determines the number of paris to consider.
       Returns axis and extra artists for extending bounding box.
    '''
    # Is false if empty
    if data:
        nplots = max(data.keys()) + 1
    else:
        nplots = 1
    fig.set_size_inches(8, 4*nplots)
    axes = fig.subplots(nplots)
    # Matplotlib will return a collection if nplots > 1, or a single object if 1
    # So we just always make it a collection... Must be a better way.
    if nplots == 1:
        axes = (axes,)
    y_labels = ["First pair", "Second pair", "Third pair", "Fourth pair"]

    final_icon = []
    for i, axis in zip(range(nplots), axes):
        working = data.get(i, Series(dtype='UInt16'))
        working = working[:num_heroes]
        if working.empty:
            axis.text(0.5, 0.5, "No Data", fontsize=14,
                      horizontalalignment='center',
                      verticalalignment='center')
            axis.yaxis.set_major_locator(MaxNLocator(integer=True))
            continue

        working.plot.bar(ax=axis, width=0.9, grid=True)

        axis.set_ylabel(y_labels[i])
        axis.yaxis.set_major_locator(MaxNLocator(integer=True))

        hero_pairs = (h.split(', ') for h in working.index)

        x_axis = axis.get_xaxis()
        x_locations = x_axis.get_major_locator()
        x_min, x_max = axis.get_xlim()
        x_range = x_max - x_min

        for h_pair, x_loc in zip(hero_pairs, x_locations.locs):
            try:
                i1 = HeroIconPrefix / convertName(h_pair[0], HeroIDType.NPC_NAME,
                                                HeroIDType.ICON_FILENAME)
            except ValueError:
                print("Unable to find hero icon for 3: " + h_pair[0])
                continue
            try:
                i2 = HeroIconPrefix / convertName(h_pair[1], HeroIDType.NPC_NAME,
                                                HeroIDType.ICON_FILENAME)
            except ValueError:
                print("Unable to find hero icon for 4: " + h_pair[1])
                continue

            y_pos1 = -0.12
            y_pos2 = -0.32
            size = 1.0

            x_rel = (float(x_loc) - x_min)/x_range
            make_image_annotation(i1, axis, x_rel, y_pos1, size)
            a2 = make_image_annotation(i2, axis, x_rel, y_pos2, size)
            # Should only need the bottom artist
            # final_icon = [a2, ]
            final_icon.append(a2)

            axis.set_xticklabels([])
            axis.yaxis.set_major_locator(MaxNLocator(integer=True))

    return fig, final_icon


def plot_pick_context(picks: DataFrame, team, r_query, fig: Figure, summarise=False, limit=None):
    '''Plots the context (in picks and bans) of a teams top picks.
       Input is a DataFrame of picks, the TeamInfo and r_query
       context.
    '''
    top_picks = picks.sum(axis=1).sort_values(ascending=False)
    fig.set_size_inches(8, 9)
    axes = fig.subplots(4, 5, sharey='row')

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

        context = pick_context(pick, team, r_query, limit=limit)
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


def get_binning_percentile_xy(df: DataFrame, bins=64, percentile=(0.7, 0.999), extent=EXTENT):
    binning = [float(x) / bins for x in range(bins)]

    xExtent = float(abs(extent[1] - extent[0]))
    xBins = [extent[0] + x * xExtent for x in binning]

    yExtent = float(abs(extent[3] - extent[2]))
    yBins = [extent[2] + y * yExtent for y in binning]

    with ChainedAssignment():
        df['xBin'] = cut(df['xCoordinate'], xBins)
        df['yBin'] = cut(df['yCoordinate'], yBins)

    # Observed limits the bins to ones with actual data in
    weightSeries = df.groupby(['xBin', 'yBin'], observed=True).size()

    return (
        weightSeries.quantile(percentile[0]),
        weightSeries.quantile(percentile[1])
    )


def get_binning_max_xy(df: DataFrame, bins=64):
    # extent is [xMin, xMax, yMin, yMax]
    step_x = (EXTENT[1] - EXTENT[0])/bins
    step_y = (EXTENT[3] - EXTENT[2])/bins

    binning_x = [EXTENT[0] + x*step_x for x in range(bins)]
    binning_y = [EXTENT[2] + y*step_y for y in range(bins)]
    working_df = DataFrame()
    working_df['xBin'] = cut(df['xCoordinate'], binning_x)
    working_df['yBin'] = cut(df['yCoordinate'], binning_y)

    weightSeries = working_df.groupby(['xBin', 'yBin'], observed=True).size()

    return weightSeries.max()


def plot_player_positioning(query_data: DataFrame, ax_in):

    # if fig_in is None:
    #     fig_in, ax_in = plt.subplots(figsize=(10, 10))
    # else:
    #     ax_in = fig_in.subplots()

    colour_map = copy.copy(mpl_colormaps.get('afmhot'))
    colour_map.set_under('black', alpha=0.0)

    vmin, vmax = get_binning_percentile_xy(query_data)

    plot = ax_in.hexbin(x=query_data['xCoordinate'],
                        y=query_data['yCoordinate'],
                        gridsize=64, mincnt=1,
                        vmin=vmin, vmax=vmax,
                        extent=[0, 1, 0, 1],
                        cmap=colour_map,
                        zorder=2)

    # Add map
    img = mpimg.imread(StaticAnalysis.CONFIG['images']['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')
    # Reposition colourbar
    # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
    divider = make_axes_locatable(ax_in)
    side_bar = divider.append_axes("right", size="5%", pad=0.05)
    cbar = ax_in.colorbar(plot, cax=side_bar)
    cbar.locator = ticker.MaxNLocator(integer=True)
    cbar.update_ticks()
    cbar.ax.tick_params(labelsize=14)

    return ax_in, side_bar, cbar.ax, plot.axes


def plot_object_position(query_data: DataFrame, bins=64,
                         fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    colour_map = copy.copy(mpl_colormaps.get('rainbow'))
    colour_map.set_under('black', alpha=0.0)
    if vmax is None:
        vmax = get_binning_max_xy(query_data, bins)
        if vmax == 1:
            vmax = 2
        vmax = vmax + 0.5
    if vmin is None:
        vmin = 1

    # Add map
    img = mpimg.imread(StaticAnalysis.CONFIG['images']['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = ax_in.hexbin(x=query_data['xCoordinate'],
                            y=query_data['yCoordinate'],
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


def plot_hero_winrates(data: DataFrame, fig: Figure, mingames=3, min_rate=0.6):
    '''Plots hero win rate over all and with a minimum games required.'''

    fig.set_size_inches(10, 10)
    axes = fig.subplots(2)
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

        # for bar, label in zip(bar_plot.patches, sub_set['Total'].iteritems()):
        for bar, label in zip(bar_plot.patches, sub_set['Total'].items()):
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

    axes[0].set_title('Win Rate')
    axes[0].set_ylabel('All')
    axes[1].set_ylabel('Min {} games'.format(mingames))

    return fig, axes


def plot_hero_lossrates(data: DataFrame, fig: Figure, mingames=3, max_rate=0.5):
    '''Plots hero win rate over all and with a minimum games required.'''

    fig.set_size_inches(10, 10)
    axes = fig.subplots(2)
    data.rename(heroShortName, inplace=True)

    def _do_plot(ax_in, data):
        sub_set: DataFrame = data.loc[data['Rate'] < max_rate]\
            .sort_values(['Rate', 'Total'], ascending=True,)

        if sub_set.empty:
            ax_in.text(0.5, 0.5, "No Data", fontsize=14,
                       horizontalalignment='center',
                       verticalalignment='center')
            ax_in.yaxis.set_major_locator(MaxNLocator(integer=True))
            return
        bar_plot = sub_set['Rate'].plot.bar(ax=ax_in)

        # for bar, label in zip(bar_plot.patches, sub_set['Total'].iteritems()):
        for bar, label in zip(bar_plot.patches, sub_set['Total'].items()):
            y = bar.get_height()
            x = bar.get_x() + bar.get_width() / 2
            ax_in.text(s=int(label[1]), x=x, y=y,
                       ha='center', va='bottom',
                       color='black')
        ax_in.set_ylim([0.0, max_rate])

    _do_plot(axes[0], data)

    subset = data.loc[data['Total'] > mingames]
    if not subset.empty:
        _do_plot(axes[1], subset)

    axes[0].set_title('Win Rate (<50%)')
    axes[0].set_ylabel('All')
    axes[1].set_ylabel('Min {} games'.format(mingames))

    return fig, axes

def plot_object_position_scatter(query_data: DataFrame, size=700,
                                 fig_in=None, ax_in=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    colour_map = copy.copy(mpl_colormaps.get('afmhot'))
    colour_map.set_under('black', alpha=0.0)

    plot = ax_in.scatter(x=query_data['xCoordinate'],
                         y=query_data['yCoordinate'],
                         c=query_data['game_time'],
                         s=size,
                         cmap='autumn_r',
                         alpha=0.5,
                         zorder=2)
    ax_in.set_xlim(EXTENT[0], EXTENT[1])
    ax_in.set_ylim(EXTENT[2], EXTENT[3])

    # Add map
    img = mpimg.imread(StaticAnalysis.CONFIG['images']['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
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


def plot_runes(rune_data: DataFrame, team: TeamInfo, fig: Figure):
    fig.set_size_inches(10, 20)
    axes = fig.subplots(4)

    bounty = rune_data[['Team Bounty', 'Opposition Bounty']]
    power = rune_data[['Team Power', 'Opposition Power']]
    water = rune_data[['Team Water', 'Opposition Water']]
    wisdom = rune_data[['Team Wisdom', 'Opposition Wisdom']]

    def _process_runes(data: DataFrame, axis, labels):
        data[labels[0]] = data.iloc[:, 0]/(data.iloc[:, 0] + data.iloc[:, 1])
        data[labels[1]] = data.iloc[:, 1]/(data.iloc[:, 0] + data.iloc[:, 1])

        data[[*labels]].plot.bar(stacked=True, ax=axis)
        xmin, xmax = axis.get_xlim()
        axis.plot((xmin, xmax), (0.5, 0.5), linewidth=3, color='r')

    power = power.resample('2min').sum()[3:13]
    _process_runes(power, axes[0], [team.name, "Opposition"])
    axes[0].set_ylabel("Power", fontsize=14)

    bounty = bounty.resample('5min').sum()[:10]
    _process_runes(bounty, axes[1], [team.name, "Opposition"])
    axes[1].set_ylabel("Bounty", fontsize=14)

    water = water.resample('2min').sum()[1:3]
    _process_runes(water, axes[2], [team.name, "Opposition"])
    axes[2].set_ylabel("Water", fontsize=14)

    wisdom = wisdom.resample('7min').sum()[1:9]
    _process_runes(wisdom, axes[3], [team.name, "Opposition"])
    axes[3].set_ylabel("Wisdom", fontsize=14)

    def _add_t_labels(ax_in, mins_per_tick: int, off_set=0):
        time_slices = len(ax_in.get_xticklabels())
        labels = []
        for x in range(time_slices):
            t1 = x*mins_per_tick + off_set
            t2 = (x+1)*mins_per_tick + off_set
            labels.append("{} to {} min".format(t1, t2))
        ax_in.set_xticklabels(labels)
        #ax_in.legend_.remove()

    _add_t_labels(axes[0], 2, off_set=6)
    _add_t_labels(axes[1], 5)
    _add_t_labels(axes[2], 2, off_set=2)
    _add_t_labels(axes[3], 7, off_set=7)

    return fig, axes
