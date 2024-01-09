import io
from dataclasses import dataclass
from datetime import datetime
from itertools import cycle
from math import ceil
from typing import Tuple

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import seaborn as sns
from herotools.HeroTools import HeroIconPrefix, HeroIDType, convertName
from herotools.important_times import ImportantTimes
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query

from pandas import DataFrame
from StaticAnalysis.analysis.visualisation import make_image_annotation_table
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TeamSelections import TeamSelections


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


# Definitions for picking/table layout
picks_patch_7_33 = OrderTimeRegion(ImportantTimes['Patch_7_33'],
                                   [5, 8, 16, 17, 23],
                                   [6, 7, 15, 18, 24],
                                   ImportantTimes['Patch_7_34'])
picks_patch_7_34 = OrderTimeRegion(ImportantTimes['Patch_7_34'],
                                   [8, 14, 15, 18, 23],
                                   [9, 13, 16, 17, 24],
                                   None)


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
def create_tables(r_query: Query, session: Session, team: TeamInfo,
                  add_text=True) -> Image:
    

    pass


def render_percent_table(df: DataFrame, min_width=50,
                         header_font_size=20, text_font_size=16):
    header_font = ImageFont.truetype('arialbd.ttf', header_font_size)
    text_font = ImageFont.truetype('arialbd.ttf', text_font_size)
    padding = 2
    widths = {k:min_width for k in df.columns}
    columns = ['Index'] + list(df.columns)
    widths['Index'] = 0
    for row in df.itertuples(name=None):
        # Use text_font for other
        for n, t in zip(columns, row):
            if n == 'Index':
                font = header_font
                pad = 4*padding + 1
            else:
                font = text_font
                pad = 2*padding
            text = str(t)
            length = ceil(font.getlength(text)) + pad
            widths[n] = max(widths[n], length)
    # Do column names too!
    for c in columns:
        if c == 'Index':
            continue
        text = str(c)
        font = header_font
        length = ceil(font.getlength(text)) + 2*padding
        widths[c] = max(widths[n], length)
    # Now make the table!
    cell_height = header_font_size + 2*padding
    font_pos = cell_height//2
    row_bg_cycle = [(255, 255, 255, 255), (220, 220, 220, 255)]
    rows = []
    # Header
    header_cells = []
    for c in columns:
        image = Image.new('RGBA', (widths[c], cell_height),
                          (255, 255, 255, 255))
        image_canvas = ImageDraw.Draw(image)
        image_canvas.line([(widths[c] - 1, 0), (widths[c]  - 1, cell_height)],
                           fill='black', width=1)
        image_canvas.line([(0, cell_height - 1), (widths[c], cell_height - 1)],
                           fill='black', width=1)
        if c != 'Index':
            font = header_font
            x = widths[c] - padding - 1
            y = font_pos
            text = str(c)
            image_canvas.text((x, y), text=text, font=font,
                              anchor="rm", align="right", fill=(0, 0, 0))
        header_cells.append(image)
    full_width = sum(x.size[0] for x in header_cells)
    image = Image.new('RGBA', (full_width, cell_height),
                       (255, 255, 255, 255))
    x, y = 0, 0
    for c in header_cells:
        image.paste(c, (x, y), c)
        x += c.size[0]
    rows.append(image)

    for row, bg in zip(df.itertuples(), cycle(row_bg_cycle)):
        cells = []
        for c, t in zip(columns, row):
            font = header_font if c == 'Index' else text_font
            image = Image.new('RGBA', (widths[c], cell_height),
                              bg)
            image_canvas = ImageDraw.Draw(image)
            image_canvas.line([(widths[c] -1, 0), (widths[c]  -1, cell_height)],
                              fill='black', width=1)
            x = widths[c] - padding - 1
            y = font_pos
            text = str(t)
            image_canvas.text((x, y), text=text, font=font,
                              anchor="rm", align="right", fill=(0, 0, 0))
            cells.append(image)

        full_width = sum(x.size[0] for x in cells)
        image = Image.new('RGBA', (full_width, cell_height),
                          bg)
        x, y = 0, 0
        for c in cells:
            image.paste(c, (x, y), c)
            x += c.size[0]
        rows.append(image)

    full_width = rows[0].size[0]
    full_height = sum(x.size[1] for x in rows)
    image = Image.new('RGBA', (full_width, full_height),
                      (255, 255, 255, 255))
    x, y = 0, 0
    for r in rows:
        image.paste(r, (x, y), r)
        y += r.size[1]

    return image

