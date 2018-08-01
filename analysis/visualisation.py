from os import environ as environment

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas import DataFrame, Series, cut, read_sql
from PIL import Image

from lib.HeroTools import HeroIconPrefix, HeroIDType, convertName

colourList = ['cool', 'summer', 'winter', 'spring', 'copper']


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
        column = column.iloc[column.nonzero()]
        column.sort_values(ascending=False, inplace=True)
        ax: Axes = column.plot.bar(ax=axis, sharey=True, colormap=colour)
        ax.set_ylabel(name)
        extra_artists = x_label_icon(ax, y_pos=-0.2, size=0.8)

        return ax, extra_artists

    extra_artists = []
    for i_ax, player in enumerate(data.columns):
        ax, extra = _plot_player(data[player], player, axes[i_ax], colour=colourList[i_ax])
        extra_artists += extra

    return figure, extra_artists


def get_binning_percentile_xy(df: DataFrame, bins=64, percentile=(0.7,0.999)):
    binning = [float(x)/bins for x in range(bins)]
    df['xBin'] = cut(df['xCoordinate'], binning)
    df['yBin'] = cut(df['yCoordinate'], binning)

    weightSeries = df.groupby(['xBin', 'yBin']).size()

    return weightSeries.quantile(percentile[0]),\
           weightSeries.quantile(percentile[1])


def plot_player_positioning(query_data: DataFrame):
    fig, ax1 = plt.subplots(figsize=(10, 13))
    jet = plt.get_cmap('afmhot')
    jet.set_under('black', alpha=0.0)

    vmin, vmax = get_binning_percentile_xy(query_data)
    plot = query_data.plot.hexbin(x='xCoordinate', y='yCoordinate',
                                  gridsize=64, mincnt=1,
                                  vmin=vmin, vmax=vmax,
                                  #interpolation='none'
                                  colormap=jet,
                                  ax=ax1, zorder=2)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax1.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax1.axis('off')

    return fig, ax1


def plot_object_position(query_data: DataFrame, bins=64, ax_in=None):
    if ax_in is None:
        fig, ax_in = plt.subplots(figsize=(10, 13))

    jet = plt.get_cmap('afmhot')
    jet.set_under('black', alpha=0.0)

    plot = ax_in.hexbin(x=query_data['xCoordinate'],
                        y=query_data['yCoordinate'],
                        gridsize=bins, mincnt=1,
                        cmap=jet,
                        zorder=2)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')

    # Reposition colourbar
    # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
    divider = make_axes_locatable(ax_in)
    side_bar = divider.append_axes("right", size="5%", pad=0.05)
    plt.colorbar(plot, cax=side_bar)

    return plot


def plot_object_position_scatter(query_data: DataFrame, size=700, ax_in=None):
    if ax_in is None:
        fig, ax_in = plt.subplots(figsize=(10, 13))

    jet = plt.get_cmap('afmhot')
    jet.set_under('black', alpha=0.0)

    plot = ax_in.scatter(x=query_data['xCoordinate'],
                         y=query_data['yCoordinate'],
                         c=query_data['game_time'],
                         s=size,
                         cmap='autumn_r',
                         alpha=0.5,
                         zorder=2)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')

    # Reposition colourbar
    # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
    divider = make_axes_locatable(ax_in)
    side_bar = divider.append_axes("right", size="5%", pad=0.05)
    plt.colorbar(plot, cax=side_bar)

    return plot