from math import ceil
from typing import List

import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
from adjustText import adjust_text
from matplotlib.axes import Axes
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.table import Table
from matplotlib.text import Text
from matplotlib.colors import to_rgba
from pandas import DataFrame, read_sql
from PIL.Image import Image, LANCZOS
from PIL.Image import open as Image_open
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query

import StaticAnalysis
from StaticAnalysis.analysis.draft_vis import (add_draft_axes,
                                               process_team_portrait)
from StaticAnalysis.analysis.visualisation import make_image_annotation2
from StaticAnalysis.lib.Common import get_player_map, seconds_to_nice, EXTENT
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Ward import Ward
from StaticAnalysis.replays.Smoke import Smoke
from herotools.location import get_modal_position
from typing import List

def build_smoke_table(query: Query, session: Session) -> DataFrame:
    """Build a table of smokes with coordinates and times.

    Arguments:
        query {Query} -- Database query with Smokes.
        session {Session} -- Session of the parsed DB.
        team_session {Session} -- Open session to team_info DB.

    Returns:
        DataFrame -- Includes x, y, steamID, times, smoke status, name.
    """
    sql_query = query.with_entities(
        Smoke.averageXCoordinateStart,
        Smoke.averageYCoordinateStart,
        Smoke.averageXCoordinateEnd,
        Smoke.averageYCoordinateEnd,
        Smoke.game_start_time
        ).statement

    data = read_sql(sql_query, session.bind)
    data.sort_values(['game_start_time'], ascending=True)

    return data

smoke_icon = Image_open(StaticAnalysis.CONFIG['images']['icons']['SMOKE_ICON'])
smoke_icon.thumbnail((24,24))
def plot_smoke_scatter(data: DataFrame, ax_in: Axes) -> list:
    """Creates a scatter plot using the images instead of points on ax_in.

    Arguments:
        data {DataFrame} -- Provides xCoordinate and yCoordinate
        ax_in {Axes} -- Target axes for the plot.
        img {Image} -- PIL Image already sized to be placed on plot.

    Returns:
        list -- List of created AnnotationBbox objects
    """
    img_boxes = []
    for _, row in data.iterrows():
            imagebox = OffsetImage(smoke_icon)
            imagebox.image.axes = ax_in
            pos = (row['averageXCoordinateStart'], row['averageYCoordinateStart'])
            ab = AnnotationBbox(imagebox, pos,
                                xycoords='data',
                                boxcoords="data",
                                box_alignment=(0.5, 0.5),
                                pad=0,
                                frameon=False)
            ax_in.add_artist(ab)
            ab.set_zorder(2)
            img_boxes.append(ab)

    return img_boxes


def plot_circle_scatter(data: DataFrame, ax_in: Axes):
    ax_in.scatter(
        data['averageXCoordinateStart'], data['averageYCoordinateStart'],
        s=1500, facecolors=to_rgba('purple', 0.5), edgecolors='purple'
        )


def smoke_start_locale(data: List[DataFrame], range=5) -> str:
     # Get the game_time for the first smoke
    smoke_start = min(
         df['game_time'][df['is_smoked']].min() for df in data
    )
    # Filtered data frame for locale determiner
    filtered_data = [
        df[
            df['is_smoked'] & df['is_alive'] & 
            df['game_time'].between(smoke_start, smoke_start+range)
        ]
        for df in data
    ]

    return get_modal_position(filtered_data)


def smoke_end_locale_first(data: List[DataFrame], prebreak=3, postbreak=3):
    first_smoke_end = min(
        df['game_time'][df['is_smoked'] & df['is_alive']].max() + 1
        for df in data
    )

    filtered_data = [
        df[
            df['is_smoked'] & df['is_alive'] & 
            df['game_time'].between(first_smoke_end - prebreak,
                                    first_smoke_end + postbreak)
        ]
        for df in data
    ]
    
    return get_modal_position(filtered_data)


def smoke_end_locale_individual(data:List[DataFrame], prebreak=3, postbreak=3):
    filtered_data = []
    for p_df in data:
        # Smoke break time
        break_time = p_df['game_time'][p_df['is_smoked'] & p_df['is_alive']].max() + 1
        filtered_data.append(
            p_df[
                p_df['is_smoked'] & p_df['is_alive'] & 
                p_df['game_time'].between(break_time - prebreak,
                                          break_time + postbreak)
            ]
        )
        
    return get_modal_position(filtered_data)