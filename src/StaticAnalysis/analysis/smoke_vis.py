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
from herotools.lib.common import SMOKE_DURATION
from herotools.location import get_modal_position
from typing import List, Tuple
from numpy import nan, isnan

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
         df.min() for x in data if not (df:=x['game_time'][x['is_smoked']]).empty
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


def smoke_start_location(data: List[DataFrame], range=5) -> Tuple[float, float]:
     # Get the game_time for the first smoke
    xCoords = []
    yCoords = []
    for df in data:
        cut = df[df['is_smoked']]
        if cut.empty:
            continue
        xCoords.append(cut['xCoordinate'].iloc[0])
        yCoords.append(cut['yCoordinate'].iloc[0])
    
    meanX = sum(xCoords)/len(xCoords)
    meanY = sum(yCoords)/len(yCoords)

    return (meanX, meanY)


def smoke_end_locale_first(data: List[DataFrame], prebreak=3, postbreak=3):
    first_smoke_end = min(
        df.max() + 1
        for x in data
        if not (df:=x['game_time'][x['is_smoked'] & x['is_alive']]).empty
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
        # Data range
        cut = p_df['game_time'][p_df['is_smoked'] & p_df['is_alive']]
        if cut.empty:
            continue
        # Smoke break time
        break_time = cut.max() + 1
        filtered_data.append(
            p_df[
                p_df['is_smoked'] & p_df['is_alive'] & 
                p_df['game_time'].between(break_time - prebreak,
                                          break_time + postbreak)
            ]
        )
        
    return get_modal_position(filtered_data)


SMOKE_OUT_OF_RANGE = object()
def get_first_smoke_start_end(
    data: List[DataFrame], min_time:int=None
    ) -> Tuple[int, int, int]:
    """
    Returns the first smoke event found by checking player smoke status in data.
    If there is no smoke then SMOKE_OUT_OF_RANGE is returned for all three.
    If the end is out of range then it is returned for the end time.
    """
    # If we have no smoke we might as well leave!
    # Without a min_time get the minimum time from the DF
    if min_time is not None:
        # min_time = min(
        # [df['game_time'].min() for df in data]
        # )
        data = [
            df[df['game_time'] >= min_time] for df in data
        ]

    no_smoke = all(
        [df[df['is_smoked']].empty for df in data]
    )
    if no_smoke:
        return (SMOKE_OUT_OF_RANGE, SMOKE_OUT_OF_RANGE, SMOKE_OUT_OF_RANGE)

    # Find first smoke
    # first_smoke = min(
    #     df[df['is_smoked']]['game_time'].min() for df in data
    # )
    first_smoke = min(
        x for df in data if not isnan(x:= df[df['is_smoked']]['game_time'].min())
    )

    # Limit the max time to the max smoke duration
    break_times = [
        df[df['is_smoked'] & (df['game_time'] <= first_smoke + SMOKE_DURATION)]['game_time'].max() + 1
        for df in data
        ]
    # Remove nan (not in smoke)
    break_times = [
        t for t in break_times if not isnan(t)
    ]
    # Find first break
    first_break = min(break_times)
    
    # Find last break
    last_break = max(break_times)

    max_time = max(
        [df['game_time'].max() for df in data]
        )
    
    if first_break > max_time:
        first_break = SMOKE_OUT_OF_RANGE

    if last_break > max_time:
        last_break = SMOKE_OUT_OF_RANGE
        
    return first_smoke, first_break, last_break


def get_smoke_time_info(data: List[DataFrame], end_location_provider=smoke_end_locale_first) -> DataFrame:
    game_time = -9000
    
    out_dict = {
        "Start time": [],
        "First break": [],
        "Last break": [],
        "Start location": [],
        "End location": [],
        "averageXCoordinateStart": [],
        "averageYCoordinateStart": [],
    }

    game_time, first_break, last_break = get_first_smoke_start_end(data, game_time)
    while game_time is not SMOKE_OUT_OF_RANGE:
        # Have to manually control things like nan as they can not be tested for equality
        if first_break is SMOKE_OUT_OF_RANGE:
            print("Smoke duration undefined as it is beyond DF range (first)")
            break
        if last_break is SMOKE_OUT_OF_RANGE:
            print("Longest duration could not be fully found as it is beyond DF range (last)")
            break
        # Fill last values
        out_dict['Start time'].append(game_time)
        out_dict['First break'].append(first_break)
        out_dict['Last break'].append(last_break)
        # Add the locales
        # cut_data = [df[df['game_time'].between(game_time, last_break + 3)] for df in data]
        cut_data = [df[df['game_time'].between(game_time, last_break + 3)] for df in data]
        out_dict['Start location'].append(smoke_start_locale(cut_data))
        out_dict['End location'].append(end_location_provider(cut_data))
        startX, startY = smoke_start_location(cut_data)
        out_dict['averageXCoordinateStart'].append(startX)
        out_dict['averageYCoordinateStart'].append(startY)

        game_time, first_break, last_break = get_first_smoke_start_end(data, last_break)

    return DataFrame(out_dict)