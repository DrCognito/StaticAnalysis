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


picks_patch_7_33 = OrderTimeRegion(ImportantTimes['Patch_7_33'],
                                   [5, 8, 16, 17, 23],
                                   [6, 7, 15, 18, 24],
                                   ImportantTimes['Patch_7_34'])
picks_patch_7_34 = OrderTimeRegion(ImportantTimes['Patch_7_34'],
                                   [8, 14, 15, 18, 23],
                                   [9, 13, 16, 17, 24],
                                   None)



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

