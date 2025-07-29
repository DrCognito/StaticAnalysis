from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from StaticAnalysis.replays.Ward import Ward
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.lib.Common import EXTENT, add_map
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Common import Team, WardType
from pandas import DataFrame, read_sql
from herotools.important_times import MAIN_TIME
from sqlalchemy import or_, and_
from StaticAnalysis.analysis.ward_vis import plot_image_scatter
from PIL.Image import open as Image_open
import StaticAnalysis
import matplotlib.pyplot as plt

liquid = get_team(2163)
replays = session.query(Replay).filter(
    liquid.filter, Replay.endTimeUTC > MAIN_TIME 
)
d_replays = replays.filter(Replay.get_side_filter(liquid, Team.DIRE)).subquery()
r_replays = replays.filter(Replay.get_side_filter(liquid, Team.RADIANT)).subquery()
dire_wards = session.query(Ward).filter(
    Ward.team == Team.DIRE, Ward.ward_type == WardType.SENTRY
    ).join(d_replays)

radiant_wards = session.query(Ward).filter(
    Ward.team == Team.RADIANT, Ward.ward_type == WardType.SENTRY
    ).join(r_replays)

mag_x = EXTENT[1] - EXTENT[0]
mag_y = EXTENT[3] - EXTENT[2]

# Accept more than x, less than y
corner_frac = 0.15
cut_in = 0.05
bottom_right_corner = (
    EXTENT[0] + (1-corner_frac)*mag_x  - cut_in*mag_x,
    EXTENT[2] + corner_frac*mag_y
)
from matplotlib.patches import Rectangle, Circle
bottom_right = Rectangle(
    xy=(EXTENT[0] + 0.76*mag_x, EXTENT[2]),
    width = mag_x*0.2,
    height = mag_y*0.2,
    alpha=0.5
)
bottom_right_wards = Rectangle(
    xy=(EXTENT[0] + 0.81*mag_x, EXTENT[2]),
    width = mag_x*0.15,
    height = mag_y*0.15,
    alpha=0.5
)
# Accept less than x, more than y
top_left_corner = (
    EXTENT[0] + corner_frac*mag_x,
    EXTENT[2] + (1-corner_frac)*mag_y - cut_in*mag_y
)
top_left = Rectangle(
    xy=(EXTENT[0], EXTENT[2] + 0.75*mag_y),
    width = mag_x*0.2,
    height = mag_y*0.2,
    alpha=0.5
)
top_left_wards = Rectangle(
    xy=(EXTENT[0], EXTENT[2] + 0.8*mag_y),
    width = mag_x*0.15,
    height = mag_y*0.15,
    alpha=0.5
)
# tormie_corners = or_(
#     and_(
#         Ward.xCoordinate >= bottom_right.get_x(),
#         Ward.yCoordinate <= bottom_right.get_y() + bottom_right.get_height()
#     ),
#     and_(
#         Ward.xCoordinate <= top_left.get_x() + top_left.get_width(),
#         Ward.yCoordinate >= top_left.get_y()
#     )
# )
bottom_right_filter = and_(
    Ward.xCoordinate >= bottom_right_wards.get_x(),
    Ward.yCoordinate <= bottom_right_wards.get_y() + bottom_right_wards.get_height()
)
top_left_filter = and_(
    Ward.xCoordinate <= top_left_wards.get_x() + top_left_wards.get_width(),
    Ward.yCoordinate >= top_left_wards.get_y()
)
tormie_corners = or_(
    top_left_filter, bottom_right_filter
)
dire_wards = dire_wards.filter(tormie_corners)
dire_df = read_sql(dire_wards.statement, session.bind)

radiant_wards = radiant_wards.filter(tormie_corners)
radiant_df = read_sql(radiant_wards.statement, session.bind)
fig = plt.figure(figsize=(10, 6))
(ax_1, ax_2) = fig.subplots(ncols=2)
ward_size = (24, 21)
# axis = fig.subplots()
# add_map(ax_t, extent=EXTENT)
# add_map(ax_b, extent=EXTENT)
ward = Image_open(StaticAnalysis.CONFIG['images']['icons']['SENTRY_ICON'])
ward.thumbnail(ward_size)
# plot_image_scatter(dire_df, axis, ward)
# axis.add_patch(top_left)
# axis.add_patch(bottom_right)
# axis.add_patch(Rectangle(
#     xy=bottom_right_corner,
#     angle=270,
#     width=corner_frac*mag_x,
#     height=corner_frac*mag_y,
#     alpha=0.5)
#     )
# axis.add_patch(Rectangle(
#     xy=top_left_corner,
#     angle=90,
#     width=corner_frac*mag_x,
#     height=corner_frac*mag_y,
#     alpha=0.5)
#     )

# axis.scatter(
#     x=dire_df['xCoordinate'], y=dire_df['yCoordinate'],
#     alpha=0.4, s=1050
# )
circler = lambda x: Circle(
        (x['xCoordinate'], x['yCoordinate']),
        radius=1050, fc=(100.0/255.0,149.0/255.0,237.0/255.0,0.3), ec="black", linewidth=1
        # radius=1050, ec="black", fc=(0.0,0.0,1.0,0.0), linewidth=1
    )

dire_df['circle'] = dire_df.apply(
    circler, axis=1
)
radiant_df['circle'] = radiant_df.apply(
    circler, axis=1
)
# from matplotlib.collections import PatchCollection
# dire_circles = PatchCollection(dire_df['circle'])
# axis.add_collection(dire_circles)
from copy import copy
def plot_corners(df: DataFrame, ax_t, ax_b, top_left: Rectangle, bottom_right: Rectangle):
    add_map(ax_t, extent=EXTENT)
    ax_t.axis('off')
    add_map(ax_b, extent=EXTENT)
    ax_b.axis('off')
    for circ in df['circle']:
        ax_t.add_patch(copy(circ))
        ax_b.add_patch(copy(circ))
    # Set top axis limits
    ax_t.set_ylim(top_left.get_y(), top_left.get_y() + top_left.get_height())
    ax_t.set_xlim(top_left.get_x(), top_left.get_x() + top_left.get_width())
    # Set bottom axis limits
    ax_b.set_ylim(bottom_right.get_y(), bottom_right.get_y() + bottom_right.get_height())
    ax_b.set_xlim(bottom_right.get_x(), bottom_right.get_x() + bottom_right.get_width())


def plot_corners_scatter(df: DataFrame, ax_t, ax_b, top_left: Rectangle, bottom_right: Rectangle):
    add_map(ax_t, extent=EXTENT)
    ax_t.axis('off')
    add_map(ax_b, extent=EXTENT)
    ax_b.axis('off')
    ax_t.scatter(
        x=df['xCoordinate'], y=df['yCoordinate'],
        alpha=1.0, marker='o', s=50, edgecolors='black'
    )
    ax_b.scatter(
        x=df['xCoordinate'], y=df['yCoordinate'],
        alpha=1.0, marker='o', s=50, edgecolors='black'
    )
    # Set top axis limits
    ax_t.set_ylim(top_left.get_y(), top_left.get_y() + top_left.get_height())
    ax_t.set_xlim(top_left.get_x(), top_left.get_x() + top_left.get_width())
    # Set bottom axis limits
    ax_b.set_ylim(bottom_right.get_y(), bottom_right.get_y() + bottom_right.get_height())
    ax_b.set_xlim(bottom_right.get_x(), bottom_right.get_x() + bottom_right.get_width())

from pandas import concat
max = dire_df[dire_df['yCoordinate'] == dire_df['yCoordinate'].max()]
# plot_corners_scatter(radiant_df, ax_1[0], ax_1[1], top_left, bottom_right)
# plot_corners_scatter(dire_df, ax_2[0], ax_2[1], top_left, bottom_right)
# plot_corners_scatter(
#     concat((dire_df, radiant_df), ignore_index=True),
#     ax_3[0], ax_3[1], top_left, bottom_right)
# plot_corners(radiant_df, ax_1[0], ax_1[1], top_left, bottom_right)
# plot_corners(dire_df, ax_2[0], ax_2[1], top_left, bottom_right)
plot_corners(
    concat((dire_df, radiant_df), ignore_index=True),
    ax_1, ax_2, top_left, bottom_right)
# plot_corners(max, ax_1[0], ax_1[1], top_left, bottom_right)
# plot_corners(max, ax_2[0], ax_2[1], top_left, bottom_right)
# plot_corners(
#     max,
#     ax_3[0], ax_3[1], top_left, bottom_right)
# ax_1[0].set_title('Radiant')
# ax_2[0].set_title('Dire')
# ax_3[0].set_title('Both')

fig.tight_layout()
fig.savefig('tormentor_sents.png')
# plt.show()

import numpy as np
def get_mesh(rect: Rectangle, bins: int):
    x_dist = np.linspace(rect.get_x(), rect.get_x() + rect.get_width(), bins)
    y_dist = np.linspace(rect.get_y(), rect.get_y() + rect.get_height(), bins)
    
    return np.meshgrid(x_dist, y_dist)
    
bins = 100

top_x, top_y = get_mesh(
    top_left,
    bins
    )
bottom_x, bottom_y = get_mesh(
    bottom_right,
    bins)

top_df = DataFrame({
    'xCoordinate': np.reshape(top_x, bins*bins),
    'yCoordinate': np.reshape(top_y, bins*bins)
    })
def circle_counter(row, circles: list[Circle]):
    total = 0
    coordinate = (row['xCoordinate'], row['yCoordinate'])
    for c in circles:
        if c.contains_point(coordinate):
            total += 1
    
    return total
from functools import partial
cc = partial(circle_counter, circles = dire_df['circle'])
# top_df['count'] = top_df.apply(cc, axis=1)

# fig, ax = plt.subplots(figsize=(8,8))
# # ax.pcolormesh(
# #     top_df['xCoordinate'],
# #     top_df['yCoordinate'],
# #     top_df['count'])
# ax.hexbin(
#     top_df['xCoordinate'],
#     top_df['yCoordinate'],
#     top_df['count']
# )
# plt.show()

# fig, ax = plt.subplots(figsize=(8,8))
# x = top_x.T
# y = top_y.T
# z = top_df['count'].values.reshape(100,100).T
# z = np.ma.masked_array(z, z < 1)
# ax.pcolormesh(x,y,z,)
def count_within_dist(row, comparisons: DataFrame, max_dist: float):
    dist_sq = max_dist * max_dist
    total = 0
    for idx, c in comparisons.iterrows():
        dist = (c['xCoordinate'] - row['xCoordinate'])**2
        dist += (c['yCoordinate'] - row['yCoordinate'])**2
        
        if dist < dist_sq:
            total += 1
    
    return total


# def heatmap(df_t: DataFrame, df_b:DataFrame, ax_t, ax_b,
#     top_left: Rectangle, bottom_right: Rectangle, bins = 100):
#     # Build our coordinate system and dfs
#     # Note as its lower and upper bounds it should be +1 for 100x100 data displayed bins!
#     top_x, top_y = get_mesh(top_left, bins+1)
#     top_df = DataFrame({
#     'xCoordinate': np.reshape(top_x, (bins+1)*(bins+1)),
#     'yCoordinate': np.reshape(top_y, (bins+1)*(bins+1))
#     })

#     bottom_x, bottom_y = get_mesh(bottom_right, bins+1)
#     bottom_df = DataFrame({
#     'xCoordinate': np.reshape(bottom_x, (bins+1)*(bins+1)),
#     'yCoordinate': np.reshape(bottom_y, (bins+1)*(bins+1))
#     })
#     # Count our ward overlaps for each point
#     # cc_t = partial(circle_counter, circles = df_t['circle'])
#     # cc_b = partial(circle_counter, circles = df_b['circle'])
#     dc_t = partial(count_within_dist, comparisons=df_t, max_dist=1050)
#     dc_b = partial(count_within_dist, comparisons=df_b, max_dist=1050)
#     top_df['count'] = top_df.apply(dc_t, axis=1)
#     bottom_df['count'] = bottom_df.apply(dc_b, axis=1)

#     # Add the maps
#     add_map(ax_t, extent=EXTENT)
#     ax_t.axis('off')
#     add_map(ax_b, extent=EXTENT)
#     ax_b.axis('off')
#     # Fix the weights
#     top_z = top_df['count'].values.reshape(101,101).T
#     top_z = np.ma.masked_array(top_z, top_z < 1)
#     bottom_z = bottom_df['count'].values.reshape(101,101).T
#     bottom_z = np.ma.masked_array(bottom_z, bottom_z < 1)
#     # Add the colour meshes
#     # These have to be transposed but I am not sure...
#     ax_t.pcolormesh(
#         top_x.T,
#         top_y.T,
#         top_z,
#         alpha=0.5)
#     ax_b.pcolormesh(
#         bottom_x.T,
#         bottom_y.T,
#         bottom_z,
#         alpha=0.5)
    
#     # Set top axis limits
#     ax_t.set_ylim(top_left.get_y(), top_left.get_y() + top_left.get_height())
#     ax_t.set_xlim(top_left.get_x(), top_left.get_x() + top_left.get_width())
#     # Set bottom axis limits
#     ax_b.set_ylim(bottom_right.get_y(), bottom_right.get_y() + bottom_right.get_height())
#     ax_b.set_xlim(bottom_right.get_x(), bottom_right.get_x() + bottom_right.get_width())
    

def heatmap(df: DataFrame, ax, 
    rect: Rectangle, bins = 100):
    # Build our coordinate system and dfs
    # Note as its lower and upper bounds it should be +1 for 100x100 data displayed bins!
    coord_x, coord_y = get_mesh(rect, bins+1)
    mesh_df = DataFrame({
    'xCoordinate': np.reshape(coord_x, (bins+1)*(bins+1)),
    'yCoordinate': np.reshape(coord_y, (bins+1)*(bins+1))
    })
    # Count our ward overlaps for each point
    # cc_t = partial(circle_counter, circles = df_t['circle'])
    dc_t = partial(count_within_dist, comparisons=df, max_dist=1050)
    mesh_df['count'] = mesh_df.apply(dc_t, axis=1)

    # Add the maps
    add_map(ax, extent=EXTENT)
    ax.axis('off')
    # Fix the weights
    coord_z = mesh_df['count'].values.reshape(bins+1,bins+1).T
    coord_z = np.ma.masked_array(coord_z, coord_z < 1)

    # Add the colour meshes
    # These have to be transposed but I am not sure...
    ax.pcolormesh(
        coord_x.T,
        coord_y.T,
        coord_z,
        alpha=0.5)
    
    # Set top axis limits
    ax.set_ylim(rect.get_y(), rect.get_y() + rect.get_height())
    ax.set_xlim(rect.get_x(), rect.get_x() + rect.get_width())


dire_wards = session.query(Ward).filter(
    Ward.team == Team.DIRE, Ward.ward_type == WardType.SENTRY
    ).join(d_replays)
radiant_wards = session.query(Ward).filter(
    Ward.team == Team.RADIANT, Ward.ward_type == WardType.SENTRY
    ).join(r_replays)

top_df = concat((
    read_sql(dire_wards.filter(top_left_filter).statement, session.bind),
    read_sql(radiant_wards.filter(top_left_filter).statement, session.bind)
    ), ignore_index=True)
bottom_df = concat((
    read_sql(dire_wards.filter(bottom_right_filter).statement, session.bind),
    read_sql(radiant_wards.filter(bottom_right_filter).statement, session.bind)
    ), ignore_index=True)
(ax_1, ax_2) = fig.subplots(ncols=2)
# heatmap(
#     top_df,
#     ax_1, top_left,)
# heatmap(
#     bottom_df,
#     ax_2, bottom_right)
# ax_1.scatter(
#         x=top_df['xCoordinate'], y=top_df['yCoordinate'],
#         alpha=1.0, marker='o', s=25, edgecolors='black'
#     )
# ax_2.scatter(
#     x=bottom_df['xCoordinate'], y=bottom_df['yCoordinate'],
#     alpha=1.0, marker='o', s=25, edgecolors='black'
# )
# fig.savefig("tormentor_sentry_heatmap.png")

# The canvas
np.zeros((100,100), 'uint8')

def generate_circle(coord_radius: float, bins: int, coverage_area: Rectangle, ax):
    x_dist = np.linspace(0, top_left.get_width(), bins+1)
    y_dist = np.linspace(0, top_left.get_height(), bins+1)
    xx, yy = np.meshgrid(x_dist, y_dist)
    # Put it in the top left
    radii2 = (xx - coverage_area.get_width() / 2) ** 2 + (yy - coverage_area.get_height() / 2 ) ** 2
    circle = radii2 < coord_radius**2
    circle = circle.astype('uint8')
    circle = np.ma.masked_array(circle, circle < 1)
    
    # Add the maps
    add_map(ax, extent=EXTENT)
    ax.axis('off')
    # Add circle
    coord_x, coord_y = get_mesh(coverage_area, bins+1)
    ax.pcolormesh(
        coord_x.T,
        coord_y.T,
        circle.T,
        alpha=0.5)
    
    # Set top axis limits
    ax.set_ylim(coverage_area.get_y(), coverage_area.get_y() + coverage_area.get_height())
    ax.set_xlim(coverage_area.get_x(), coverage_area.get_x() + coverage_area.get_width())
    

(ax_1, ax_2) = fig.subplots(ncols=2)
generate_circle(
    coord_radius=1050,
    bins=100,
    coverage_area=top_left,
    ax=ax_1
)

x_dist = np.linspace(0, top_left.get_width(), bins)
y_dist = np.linspace(0, top_left.get_height(), bins)
xx, yy = np.meshgrid(x_dist, y_dist)
# Put it in the top left
radii2 = (xx - 1050) ** 2 + (yy - 1050) ** 2
circle = radii2 < 1050**2
circle = circle.astype('uint8')