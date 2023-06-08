from StaticAnalysis.tests.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.ward_vis import plot_image_scatter, plot_eye_scatter, plot_map
from StaticAnalysis.analysis.Replay import get_ptbase_tslice
from StaticAnalysis.analysis.visualisation import dataframe_xy_time, get_binning_max_xy, make_axes_locatable
from StaticAnalysis.replays.Ward import Ward, WardType
import matplotlib.pyplot as plt
from herotools.important_times import ImportantTimes
from PIL.Image import open as Image_open
from os import environ as environment
import copy
import matplotlib.image as mpimg
from StaticAnalysis.lib.Common import EXTENT
from matplotlib import ticker
from pandas import DataFrame
from adjustText import adjust_text

replay_limit = 20  # !?
team_liquid: TeamInfo
team_liquid = team_session.query(TeamInfo).filter(TeamInfo.team_id == 2163).one()
cut_time = ImportantTimes['After_Berlin']

r_filter = Replay.endTimeUTC >= cut_time
r_query = team_liquid.get_replays(session).filter(r_filter)
team = team_liquid

wards_dire, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                              Type=Ward,
                                              start=-2*60, end=12*60,
                                              replay_limit=replay_limit)
wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)

dire_df = dataframe_xy_time(wards_dire, Ward, session)
radiant_df = dataframe_xy_time(wards_radiant, Ward, session)

fig = plt.figure(figsize=(8.27, 11.69))


def plot_object_position(query_data: DataFrame, bins=8,
                         ax_in=None, vmin=None, vmax=None):

    ward = Image_open(environment['WARD_ICON'])
    ward.thumbnail((7, 17))
    wards = plot_image_scatter(query_data, ax_in, ward)

    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)
    if vmax is None:
        vmax = get_binning_max_xy(query_data, bins)
        if vmax == 1:
            vmax = 2
        vmax = vmax + 0.5
    if vmin is None:
        vmin = 1

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if query_data.empty:
        return ax_in

    plot = ax_in.hexbin(x=query_data['xCoordinate'],
                        y=query_data['yCoordinate'],
                        gridsize=bins, mincnt=0,
                        extent=EXTENT,
                        cmap=colour_map,
                        vmin=vmin, vmax=vmax,
                        zorder=1, alpha=0.5, lw=0)

    texts = []
    counts = plot.get_array()
    total = sum(counts)
    percents = [round(x/total*100.0, 1) for x in counts]
    verts = plot.get_offsets()
    for offc in range(verts.shape[0]):
        binx, biny = verts[offc][0], verts[offc][1]
        if percents[offc]:
            # plt.plot(binx, biny, 'k.', zorder=100)
            texts.append(ax_in.text(binx, biny, f"{percents[offc]}%", zorder=100, ha='center', va='center'))
    # Jiggle text around
    adjust_text(texts, add_objects=wards)
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


def _process(df: DataFrame, fig, out):
    ax = fig.subplots()
    plot_object_position(df, ax_in=ax)
    fig.tight_layout()
    fig.savefig(out)
    fig.clf()


def _plot_typical(ward_df: DataFrame, fig):
    _process(ward_df.loc[ward_df['game_time'] <= 0], fig, "pregame.png")
    _process(ward_df.loc[(ward_df['game_time'] > 0) &
                         (ward_df['game_time'] <= 4*60)], fig, "0to4.png")
    _process(ward_df.loc[(ward_df['game_time'] > 4*60) &
                         (ward_df['game_time'] <= 8*60)], fig, "4to8.png")
    _process(ward_df.loc[(ward_df['game_time'] > 8*60) &
                         (ward_df['game_time'] <= 12*60)], fig, "8to16.png")


# plot_object_position(dire_df, ax_in=ax)
# fig.tight_layout()
# plt.show()
_plot_typical(dire_df, fig)
