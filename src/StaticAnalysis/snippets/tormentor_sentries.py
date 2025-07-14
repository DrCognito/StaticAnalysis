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
    xy=(EXTENT[0], EXTENT[2] + 0.8*mag_y),
    width = mag_x*0.15,
    height = mag_y*0.15,
    alpha=0.5
)
tormie_corners = or_(
    and_(
        Ward.xCoordinate >= bottom_right.get_x(),
        Ward.yCoordinate <= bottom_right.get_y() + bottom_right.get_height()
    ),
    and_(
        Ward.xCoordinate <= top_left.get_x() + top_left.get_width(),
        Ward.yCoordinate >= top_left.get_y()
    )
)
dire_wards = dire_wards.filter(tormie_corners)
dire_df = read_sql(dire_wards.statement, session.bind)

radiant_wards = radiant_wards.filter(tormie_corners)
radiant_df = read_sql(radiant_wards.statement, session.bind)
fig = plt.figure(figsize=(8, 12))
(ax_1, ax_2, ax_3) = fig.subplots(ncols=2, nrows=3)
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
        radius=1050/2, alpha=0.5, ec="gray", fc="CornflowerBlue"
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
plot_corners_scatter(radiant_df, ax_1[0], ax_1[1], top_left, bottom_right)
plot_corners_scatter(dire_df, ax_2[0], ax_2[1], top_left, bottom_right)
plot_corners_scatter(
    concat((dire_df, radiant_df), ignore_index=True),
    ax_3[0], ax_3[1], top_left, bottom_right)
ax_1[0].set_title('Radiant')
ax_2[0].set_title('Dire')
ax_3[0].set_title('Both')

fig.tight_layout()
fig.savefig('tormentor_sents.png')
plt.show()