from dataclasses import dataclass
from datetime import datetime
from itertools import cycle
from math import ceil

from herotools.HeroTools import HeroIconPrefix, HeroIDType, convertName
from herotools.important_times import ImportantTimes
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query

from pandas import DataFrame
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.TeamSelections import TeamSelections, PickBans
from StaticAnalysis import session, team_session
from PIL.ImageFont import FreeTypeFont
from sqlalchemy import and_
from pandas import Series, concat, pivot_table, read_sql
from collections import Counter
from StaticAnalysis.lib.Common import get_player_name

@dataclass
class OrderTimeRegion:
    start: datetime
    first_pick: list
    second_pick: list
    end: datetime = None


@dataclass
class ColumnDesc:
    columns: tuple
    name: str
    rel_width: float


# Placeholder for a divider in the table
DIVIDER = object()

# Definitions for picking/table layout
picks_patch_7_33 = OrderTimeRegion(ImportantTimes['Patch_7_33'],
                                   [5, 8, 16, 17, 23],
                                   [6, 7, 15, 18, 24],
                                   ImportantTimes['Patch_7_34'])
picks_patch_7_34 = OrderTimeRegion(ImportantTimes['Patch_7_34'],
                                   [8, 14, 15, 18, 23],
                                   [9, 13, 16, 17, 24],
                                   None)

CURRENT_PATCH = picks_patch_7_34


table_desc = [
    ColumnDesc((8,), "8", 1.0),
    ColumnDesc((9,), "9", 1.0),
    DIVIDER,
    ColumnDesc((13,), "13", 1.0),
    ColumnDesc((14, 15,), "14 and 15", 2.0),
    ColumnDesc((16, 17,), "16 and 17", 2.0),
    ColumnDesc((18,), "18", 1.0),
    DIVIDER,
    ColumnDesc((23,), "23", 1.0),
    ColumnDesc((24,), "24", 1.0),
]

# Description for percent tables.
# Column headers are strings that match the table
percent_desc = [
    ColumnDesc(("8",), "8", 1.0),
    ColumnDesc(("9",), "9", 1.0),
    ColumnDesc(("8", "9"), "1st Phase", 1.0),
    ColumnDesc(("13",), "13", 1.0),
    ColumnDesc(("14 and 15",), "14 and 15", 1.0),
    ColumnDesc(("16 and 17",), "16 and 17", 1.0),
    ColumnDesc(("18",), "18", 1.0),
    ColumnDesc(("13", "14 and 15", "16 and 17", "18"), "2nd Phase", 1.0),
    ColumnDesc(("23",), "23", 1.0),
    ColumnDesc(("24",), "24", 1.0),
    ColumnDesc(("23", "24"), "Final Phase", 1.0),
]


@dataclass
class TableProperties:
    hero_size: int
    padding: int
    heroes_per_row: int
    count_font_size: int
    header_size: int
    header_font_size: int
    divider_spacing: int
    font: FreeTypeFont


# Definition for table styling
table_setup = TableProperties(
    hero_size=22,
    padding=2,
    heroes_per_row=5,
    count_font_size=16,
    header_size=22,
    header_font_size=22 - 2,  # header_size - padding
    divider_spacing=5,
    # font = ImageFont.truetype('arialbd.ttf', self.table.count_font_size)
    font='arialbd.ttf'
)
# Divider image, also used as placeholder
divider = Image.new('RGBA', (table_setup.divider_spacing, table_setup.padding), (255, 255, 255, 0))


def draw_cell_image(heroes: Counter, table_setup: TableProperties, width_scale: float = 1.0) -> Image:
    '''
    Draws a "cell" of heroes from a counter container according to table_setup.
    '''
    # For reference, PIL image coordinate system is (0, 0) is the upper left corner!
    # Initial image properties from table properties
    heroes_per_row = ceil(table_setup.heroes_per_row * width_scale)
    n_rows = ceil(len(heroes) / heroes_per_row)

    width = (
        table_setup.padding
        + min(len(heroes), heroes_per_row)
        * (table_setup.hero_size + table_setup.padding)
    )
    height = (
        table_setup.padding
        + (2 * table_setup.padding + table_setup.hero_size + table_setup.count_font_size)
        * n_rows
    )
    # Adjustment for final row
    # Image setup
    cell_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    cell_canvas = ImageDraw.Draw(cell_image)
    count_font = ImageFont.truetype(table_setup.font, table_setup.count_font_size)

    # Setup iters to use as cursors
    # x_iter is just a range of hero sized spacing up to the edge (width)
    x_iter = range(table_setup.padding, width, table_setup.hero_size + table_setup.padding)
    # y_iter uses full size of hero and text with pad, repeats for n_cols each row
    y_iter = []
    for i in range(n_rows):
        y_pos = (table_setup.padding
                 + i * (2 * table_setup.padding + table_setup.hero_size + table_setup.count_font_size))
        y_iter += [y_pos] * heroes_per_row
    assert (len(y_iter) >= len(heroes))

    for (h, c), x, y in zip(heroes.most_common(), cycle(x_iter), y_iter):
        # Adjusted locations as icon is bellow text and text is centered
        # y_icon = y + table_setup.padding + table_setup.count_font_size
        y_icon = y
        y_text = y + table_setup.padding + table_setup.hero_size
        x_text = x + table_setup.hero_size // 2

        # Get the hero icon
        try:
            # Get and resize the hero icon.
            icon = HeroIconPrefix / convertName(h, HeroIDType.NPC_NAME,
                                                HeroIDType.ICON_FILENAME)
        except (ValueError, KeyError):
            print("Unable to find hero icon for (table): " + h)
            continue
        # Paste it in
        h_icon = Image.open(icon)
        h_icon = h_icon.resize((table_setup.hero_size, table_setup.hero_size))
        cell_image.paste(h_icon, (x, y_icon))

        # Add the text
        if c > 1:
            cell_canvas.text(
                (x_text, y_text), text=str(c),
                font=count_font,
                anchor="mt", align="right", fill=(0, 0, 0)
            )

    return cell_image


def draw_name(name: str, table_setup: TableProperties) -> Image:
    '''
    Draws a name image according to table_setup.
    '''
    font = ImageFont.truetype('arialbd.ttf', table_setup.header_font_size)
    width = (
        4 * table_setup.padding
        + int(font.getlength(name))
    )
    height = (
        4 * table_setup.padding
        + table_setup.header_font_size
    )
    # Right justified
    x_text = width - table_setup.padding
    y_text = 2 * table_setup.padding

    name_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    name_canvas = ImageDraw.Draw(name_image)

    name_canvas.text((x_text, y_text), anchor="rt",
                     font=font, fill=(0, 0, 0), align="right",
                     text=name)

    return name_image


def draw_header(title: str, table_setup: TableProperties) -> Image:
    '''
    Draws a header title image according to table_setup.
    '''
    font = ImageFont.truetype('arialbd.ttf', table_setup.header_font_size)
    width = (
        2 * table_setup.padding
        + int(font.getlength(title))
    )
    height = (
        4 * table_setup.padding
        + table_setup.header_font_size
    )
    # Right justified
    x_text = width - table_setup.padding
    y_text = 2*table_setup.padding

    header_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    header_canvas = ImageDraw.Draw(header_image)

    header_canvas.text((x_text, y_text), anchor="rt",
                       font=font, fill=(0, 0, 0), align="right",
                       text=title)

    return header_image


def build_table_query(r_query: Query, sess: Session, team: TeamInfo, firstPick: bool) -> Query:
    # Get Team Selections first
    _team_filter = team.custom_filter(TeamSelections.teamID, TeamSelections.stackID)
    selections_query = (
        sess.query(TeamSelections)
        .filter(_team_filter)
        .filter(TeamSelections.firstPick == firstPick)
        .join(r_query.subquery())
        )

    # Get corresponding pick bans by joining on a sub_query of selections
    sq = selections_query.subquery()
    pickbans_query = (
        sess.query(PickBans)
        .filter(PickBans.is_pick == True)
        .join(sq, and_(sq.c.replay_ID == PickBans.replayID, sq.c.team == PickBans.team))
    )

    return pickbans_query


def verify_fix_order(df_in: DataFrame, order: list):
    broken = df_in.loc[~df_in['order'].isin(order)]
    if broken.empty:
        return
    r_ids = broken.loc[:, 'replayID'].unique()
    print(f"Broken pick ban pattern in: {r_ids}")

    for r in r_ids:
        section = df_in.loc[df_in['replayID'] == r, 'order']
        # Limit to the length of the part
        df_in.loc[df_in['replayID'] == r, 'order'] = order[:len(section)]

    return


def process_df(first_df: DataFrame, second_df: DataFrame,
               team_session: Session, team: TeamInfo,
               desc=table_desc) -> DataFrame:
    if first_df.empty:
        pick_df = second_df
    elif second_df.empty:
        pick_df = first_df
    else:
        pick_df = concat([first_df, second_df], ignore_index=True)
    # Pivot provides a more natural representation, moving the order out to columns
    pick_df = pivot_table(pick_df, index='playerID', columns='order',
                          values='hero', aggfunc=Counter, fill_value=Counter())
    pick_df = pick_df.reset_index()
    # Build the final table
    out_df = DataFrame()
    # Names for the first column
    out_df['Name'] = pick_df['playerID'].apply(lambda x: get_player_name(team_session, x, team))

    c: ColumnDesc
    for c in desc:
        if c is DIVIDER:
            continue
        out_df[c.name] = pick_df.loc[:, c.columns].sum(axis=1)

    return out_df


def image_table(counter_df: DataFrame, table_desc: list, table_setup: TableProperties):
    out_df = DataFrame()
    # Names
    names = [divider, ]
    for _, n in counter_df['Name'].items():
        names.append(draw_name(n, table_setup))
    out_df['Names'] = names

    div_count = 1
    col: ColumnDesc
    for col in table_desc:
        if col is DIVIDER:
            # Dividers all the way down so we can facilitate getting widths and max heights!
            out_df[f'DIVIDER{div_count}'] = [divider] * len(names)
            div_count += 1
        else:
            c = [draw_header(col.name, table_setup), ]
            for _, heroes in counter_df[col.name].items():
                c.append(draw_cell_image(heroes, table_setup, col.rel_width))
            out_df[col.name] = c

    return out_df


def draw_table(image_df: DataFrame, table_setup: TableProperties) -> Image:
    # Spacing calculations
    col_widths = [0, ]
    sum_width = 0
    # .items is over columns
    for _, c in image_df.items():
        max_width = max(c.apply(lambda x: x.size[0]))
        sum_width += max_width + 1
        col_widths.append(sum_width)

    col_heights = [0, ]
    sum_height = 0
    for _, r in image_df.iterrows():
        max_height = max(r.apply(lambda x: x.size[1]))
        sum_height += max_height + 1
        col_heights.append(sum_height)

    # Image setup
    table_image = Image.new('RGBA', (sum_width, sum_height), (255, 255, 255, 0))
    table_canvas = ImageDraw.Draw(table_image)
    # Add stripes, skipping headers
    row_bg_cycle = [(255, 255, 255, 255), (220, 220, 220, 255)]
    for r_bg, y1, y2 in zip(cycle(row_bg_cycle), col_heights[:-1], col_heights[1:]):
        table_canvas.rectangle(
            [(0, y1), (sum_width, y2)],
            fill=r_bg,
        )
    # Add lines
    # vertical
    table_canvas.line(xy=[(0, sum_height), (0, 0)],
                      fill=(0, 0, 0, 255),
                      width=1
                      )
    for x in col_widths:
        table_canvas.line([(x, sum_height), (x, 0)],
                          fill=(0, 0, 0, 255),
                          width=1
                          )
    # horizontal
    # table_canvas.line([(sum_width, 0), (0, 0)],
    #                   fill=(0, 0, 0, 255),
    #                   width=1
    #                   )
    for y in col_heights:
        table_canvas.line([(sum_width, y), (0, y)],
                          fill=(0, 0, 0, 255),
                          width=1
                          )

    # header text, right aligned
    # y = table_setup.padding
    y = 0
    for (_, img), x in zip(image_df.loc[0].items(), col_widths[1:]):
        x_img = x - img.size[0]
        table_image.paste(img, (x_img, y), img)
    # name text right aligned, skip top one
    x = col_widths[1]
    for (_, img), y in zip(image_df.iloc[1:, 0].items(), col_heights[1:]):
        x_img = x - img.size[0]
        table_image.paste(img, (x_img, y), img)

    # Paste in the cells.
    # Go row by row on a fixed y.
    # Get each cell in each row and iterate over x as widths.
    for (_, row), y in zip(image_df.iloc[1:].iterrows(), col_heights[1:-1]):
        for img, x in zip(row[1:], col_widths[1:-1]):
            table_image.paste(img, (x, y), img)
            pass

    return table_image


def percent_table(counter_df: DataFrame, desc: list = percent_desc) -> DataFrame:
    # Get totals from counter total function, temp for calculating totals for counters.
    # Skip the first column as it should be names
    temp = counter_df.iloc[:, 1:].map(lambda x: x.total())
    totals = temp.sum(axis=1)
    # Add the name back
    out_df = DataFrame()
    out_df['Name'] = counter_df['Name']
    # Add the summary columns
    for col in desc:
        name, cols = col.name, col.columns
        # Convert totals to percents
        out_df[name] = (temp.loc[:, cols].divide(totals, axis=0).multiply(100).sum(axis=1))
        # Nice formatting for percents
        out_df[name] = out_df[name].map(lambda x: f"{x:.0f}%")

    return out_df


def draw_percent(percent_table: DataFrame, table_setup: TableProperties) -> Image:
    image_df = DataFrame()
    image_df['Name'] = concat(
                        [Series(divider),
                         percent_table['Name'].map(lambda x: draw_name(x, table_setup))]
                         )
    for name, col in percent_table.loc[:, percent_table.columns != "Name"].items():
        # c = Series(draw_header(name, table_setup))
        image_df[name] = concat([Series(draw_header(name, table_setup)),
                                 col.map(lambda x: draw_name(x, table_setup))])
    # Handle our weird concat behaviour
    image_df = image_df.reset_index(drop=True)

    # Spacing calculations
    col_widths = [0, ]
    sum_width = 0
    # .items is over columns
    for _, c in image_df.items():
        max_width = max(c.apply(lambda x: x.size[0]))
        sum_width += max_width + 1
        col_widths.append(sum_width)

    col_heights = [0, ]
    sum_height = 0
    for _, r in image_df.iterrows():
        max_height = max(r.apply(lambda x: x.size[1]))
        sum_height += max_height + 1
        col_heights.append(sum_height)

    # Image setup
    table_image = Image.new('RGBA', (sum_width, sum_height), (255, 255, 255, 0))
    table_canvas = ImageDraw.Draw(table_image)
    # Add stripes, skipping headers
    row_bg_cycle = [(255, 255, 255, 255), (220, 220, 220, 255)]
    for r_bg, y1, y2 in zip(cycle(row_bg_cycle), col_heights[:-1], col_heights[1:]):
        table_canvas.rectangle(
            [(0, y1), (sum_width, y2)],
            fill=r_bg,
        )
    # Add lines
    # vertical
    table_canvas.line(xy=[(0, sum_height), (0, 0)],
                      fill=(0, 0, 0, 255),
                      width=1
                      )
    for x in col_widths:
        table_canvas.line([(x, sum_height), (x, 0)],
                          fill=(0, 0, 0, 255),
                          width=1
                          )
    # horizontal
    # table_canvas.line([(sum_width, 0), (0, 0)],
    #                   fill=(0, 0, 0, 255),
    #                   width=1
    #                   )
    for y in col_heights:
        table_canvas.line([(sum_width, y), (0, y)],
                          fill=(0, 0, 0, 255),
                          width=1
                          )

    # header text, right aligned
    # y = table_setup.padding
    y = 0
    for (_, img), x in zip(image_df.loc[0].items(), col_widths[1:]):
        x_img = x - img.size[0]
        table_image.paste(img, (x_img, y), img)
    # name text right aligned, skip top one
    x = col_widths[1]
    for (_, img), y in zip(image_df.iloc[1:, 0].items(), col_heights[1:]):
        x_img = x - img.size[0]
        table_image.paste(img, (x_img, y), img)

    # Paste in the cells.
    # Go row by row on a fixed y.
    # Get each cell in each row and iterate over x as widths.
    # Unlike previous table, the right alignment means we start with second third width
    for (_, row), y in zip(image_df.iloc[1:].iterrows(), col_heights[1:-1]):
        for img, x in zip(row[1:], col_widths[2:]):
            x = x - img.size[0]
            table_image.paste(img, (x, y), img)
            pass

    return table_image


def create_tables(r_query: Query,
                  team: TeamInfo,
                  sess: Session = session, team_sess: Session = team_session) -> Image:
    # Get queries
    first_query = build_table_query(r_query, sess, team, firstPick=True)
    second_query = build_table_query(r_query, sess, team, firstPick=False)

    # Make tables from queries
    first_df = read_sql(first_query.statement, sess.bind)
    second_df = read_sql(second_query.statement, sess.bind)

    # Normalise the pick inputs incase of some funny business
    verify_fix_order(first_df, CURRENT_PATCH.first_pick)
    verify_fix_order(second_df, CURRENT_PATCH.second_pick)

    # Final processing
    final_df = process_df(first_df, second_df, team_sess, team)
    image_df = image_table(final_df, table_desc, table_setup)

    # Image of the picks
    pick_image = draw_table(image_df, table_setup)

    # Percent table
    percent_df = percent_table(final_df)
    percent_image = draw_percent(percent_df, table_setup)

    # Combine the two images
    spacing = 50
    width = max(pick_image.size[0], percent_image.size[0])
    height = pick_image.size[1] + percent_image.size[1] + spacing

    final = Image.new('RGBA', (width, height),
                    (255, 255, 255, 255))
    x, y = 0, 0
    final.paste(pick_image, (x, y), pick_image)
    y += pick_image.size[1] + spacing
    final.paste(percent_image, (x, y), percent_image)

    return final
