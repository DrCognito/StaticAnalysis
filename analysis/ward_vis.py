from replays.Replay import Replay, Team
from replays.TeamSelections import TeamSelections
from replays.Ward import Ward
from lib.Common import seconds_to_nice, get_player_map
from pandas import DataFrame, read_sql
from sqlalchemy.orm.query import Query
from sqlalchemy.orm import Session
from matplotlib.text import Text
from matplotlib.axes import Axes
from typing import List
import matplotlib.image as mpimg
from os import environ as environment
from adjustText import adjust_text
import matplotlib.patheffects as PathEffects
from matplotlib.table import Table
from math import ceil
from PIL.Image import Image
from PIL.Image import open as Image_open
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from analysis.draft_vis import add_draft_axes, process_team


def build_ward_table(query: Query, session: Session,
                     team_session: Session) -> DataFrame:
    """Build a table of wards with coordinates, IDs, names and times.
    
    Arguments:
        query {Query} -- Database query with Wards.
        session {Session} -- Session of the parsed DB.
        team_session {Session} -- Open session to team_info DB.
    
    Returns:
        DataFrame -- Includes x, y, steamID, times, smoke status, name.
    """
    sql_query = query.with_entities(Ward.xCoordinate,
                                    Ward.yCoordinate,
                                    Ward.steamID,
                                    Ward.game_time,
                                    Ward.from_smoke).statement

    data = read_sql(sql_query, session.bind)
    data.sort_values(['game_time'], ascending=True)

    name_map = get_player_map(team_session, set(data['steamID'].unique()))
    data['Name'] = data['steamID'].map(name_map)
    data['time'] = data['game_time'].map(seconds_to_nice)

    return data


def plot_labels(data: DataFrame, ax_in: Axes,
                text_kwargs: dict={}) -> List[Text]:
    """Plots text in data['label'] using xCoordinate and yCoordinate.
    List of text objects are returned for further use.

    Arguments:
        data {DataFrame} -- DataFrame, must include xCoordinate, yCoordinate
         and label
        ax_in {Axes} -- Axes object to plot on.

    Keyword Arguments:
        text_kwargs {dict} -- Optional text kwargs. (default: {{}})

    Returns:
        List[Text] -- List of Text objects created during plotting.
    """
    text_items = []
    for _, row in data.iterrows():
        txt = ax_in.text(x=row['xCoordinate'], y=row['yCoordinate'],
                         s=row['label'],
                         **text_kwargs)
        text_items.append(txt)

    return text_items


def label_smoke_name_time(data: DataFrame) -> DataFrame:
    """Creates a label column with format (s) name time

    Arguments:
        data {DataFrame} -- DataFrame containing name, smoke status and time.

    Returns:
        DataFrame -- DataFrame with the new label column added.
    """
    labels = []

    for _, row in data.iterrows():
        if row['anon_1']:
            text = "(s){} {}".format(row['Name'], row['time'])
        else:
            text = "{} {}".format(row['Name'], row['time'])

        labels.append(text)

    data['label'] = labels

    return data


def plot_map(ax_in: Axes):
    """Plot map in the standard manner.

    Arguments:
        ax_in {Axes} -- Axes for the map!
    """
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')
    ax_in.set_xlim(0, 1)
    ax_in.set_ylim(0, 1)


def plot_sum_table(data: DataFrame, ax_in: Axes) -> Table:
    """Add a summary table to axes. Location is at the bottom. Default format
    is split into two side by side. Kind of hacky.

    Arguments:
        data {DataFrame} -- DataFrame containing label, name, time, smoke info.
        ax_in {Axes} -- Axes to display table.

    Returns:
        Table -- Plotted Table object.
    """
    split = ceil(data.shape[0]/2)
    summary_table = DataFrame()

    summary_table['label'] = data['label'][:split]
    summary_table['Name'] = data['Name'][:split]
    summary_table['time'] = data['time'][:split]
    summary_table['smoked'] = data['anon_1'][:split]

    summary_table['label2'] = data['label'][split:].reset_index()['label']
    summary_table['Name2'] = data['Name'][split:].reset_index()['Name']
    summary_table['time2'] = data['time'][split:].reset_index()['time']
    summary_table['smoked2'] = data['anon_1'][split:].reset_index()['anon_1']

    # Nicer labels
    summary_table['smoked2'] = summary_table['smoked2'].map({True: 'Y',
                                                             False: 'N'})
    summary_table['smoked'] = summary_table['smoked'].map({True: 'Y',
                                                           False: 'N'})

    # Needed in case we have uneven numbers
    summary_table.fillna(value='', inplace=True)

    table = ax_in.table(cellText=summary_table.values,
                        loc='bottom',
                        colWidths=[0.05, 0.2, 0.1, 0.15, 0.05, 0.2, 0.1, 0.15],
                        colLabels=["", "Name", "Time", "Smoked",
                                   "", "Name", "Time", "Smoked"])

    return table


def plot_image_scatter(data: DataFrame, ax_in: Axes, img: Image) -> list:
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
            imagebox = OffsetImage(img)
            imagebox.image.axes = ax_in
            pos = (row['xCoordinate'], row['yCoordinate'])
            ab = AnnotationBbox(imagebox, pos,
                                xycoords='data',
                                boxcoords="offset points",
                                box_alignment=(0.5, 0.5),
                                pad=0,
                                frameon=False)
            ax_in.add_artist(ab)
            ab.set_zorder(2)
            img_boxes.append(ab)

    return img_boxes


def plot_full_text(data: DataFrame, ax_in: Axes) -> list:
    """Performs standard formatted full-text plot on ax_in.

    Arguments:
        data {DataFrame} -- DataFrame with x,y coordinates, smoke,
         names, times.
        ax_in {Axes} -- Axes to receive plot.

    Returns:
        list -- Returns any extra ents generated during process.

    """

    plot_map(ax_in)
    data = label_smoke_name_time(data)

    text_style = {'color': 'blue',
                  'va': 'bottom',
                  'ha': 'left',
                  'path_effects': [PathEffects.withStroke(linewidth=3,
                                   foreground="w")]}
    text_ents = plot_labels(data, ax_in, text_style)

    arrow_style = dict(arrowstyle='->', color='r', lw=2)
    adjust_text(text_ents,
                ax=ax_in,
                arrowprops=arrow_style)

    return text_ents


def plot_num_table(data: DataFrame, ax_in: Axes) -> list:
    """Plots standard formatted plot with number labels on map and table summary.

    Arguments:
        data {DataFrame} -- Table with xCoordinate, yCoordinate, time,
         smoke and Name
        ax_in {Axes} -- Target axes for plot

    Returns:
        list -- Returns list of generated plot entities.
    """
    # Map
    plot_map(ax_in)

    # Add labels
    data['label'] = [str(x + 1) for x in range(data.shape[0])]
    text_style = {'color': 'blue',
                  'va': 'bottom',
                  'ha': 'left',
                  'path_effects': [PathEffects.withStroke(linewidth=3,
                                   foreground="w")],
                  'fontsize': 14}
    text_ents = plot_labels(data, ax_in, text_style)

    # Adjust the labels
    adjust_text(text_ents, ax=ax_in)

    # Add summary table
    table = plot_sum_table(data, ax_in)

    return text_ents.append(table)


def plot_eye_scatter(data: DataFrame, ax_in: Axes,
                     size: (int, int) = (35, 27)) -> list:
    """Standard formatted plot with eye ward symbol scatter.

    Arguments:
        data {DataFrame} -- Table with xCoordinate, yCoordinate, time,
         smoke and Name
        ax_in {Axes} -- Target axes for plot
    
    Keyword Arguments:
        size {[type]} -- Image size (default: {(14, 34)})
    
    Returns:
        list -- Returns list of generated plot entities.
    """
    # Map
    plot_map(ax_in)

    # Add labels
    #data = label_smoke_name_time(data)
    data['label'] = [str(x + 1) for x in range(data.shape[0])]
    text_style = {'color': 'blue',
                  'va': 'bottom',
                  'ha': 'left',
                  'path_effects': [PathEffects.withStroke(linewidth=3,
                                   foreground="w")],
                  'fontsize': 14}
    text_ents = plot_labels(data, ax_in, text_style)

    ward = Image_open(environment['WARD_ICON'])
    ward.thumbnail(size)
    extra_ents = plot_image_scatter(data, ax_in, ward)

    # Adjust the labels
    adjust_text(text_ents, extra_ents=extra_ents, ax=ax_in)

    # Add summary table
    table = plot_sum_table(data, ax_in)

    return text_ents + extra_ents


def plot_drafts(r_query: Query, ax_in: Axes,
                r_name: str="Opposition",
                d_name: str="Opposition") -> list:
    """Plot the draft lines from a replay onto an axes

    Arguments:
        replay {Replay} -- Replay object containing the TeamSelections.
        ax_in {Axes} -- Axes to plot on.

    Keyword Arguments:
        r_name {str} -- Radiant team name. (default: {"Opposition"})
        d_name {str} -- Dire team name. (default: {"Opposition"})

    Returns:
        list -- List of generated plotted objects.
    """
    replay = r_query.one()
    for t in replay.teams:
        if t.team == Team.RADIANT:
            rdraft = process_team(replay, t)
        else:
            ddraft = process_team(replay, t)

    r_draft_box = add_draft_axes(rdraft, ax_in, height=0.075)
    r_name_box = ax_in.text(s=r_name, x=0, y=0.08,
                            path_effects=[PathEffects.withStroke(linewidth=3,
                                          foreground="w")],
                            ha='left', va='bottom')

    d_draft_box = add_draft_axes(ddraft, ax_in, height=0.075,
                                 origin_br=False, origin=(1, 1))
    d_name_box = ax_in.text(s=d_name, x=1.0, y=1.0 - 0.08,
                            path_effects=[PathEffects.withStroke(linewidth=3,
                                          foreground="w")],
                            ha='right', va='top')

    return [r_draft_box, r_name_box, d_draft_box, d_name_box]
