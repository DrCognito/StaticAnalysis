import os
import sys
from typing import Tuple


import StaticAnalysis.tests.minimal_db as db
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.TeamSelections import PickBans, TeamSelections

from StaticAnalysis.lib.team_info import TeamInfo

import matplotlib.pyplot as plt

from os import environ as environment
from dotenv import load_dotenv
from StaticAnalysis.analysis.ward_vis import colour_list, plot_labels
from pandas import DataFrame, Interval, IntervalIndex, cut, read_sql
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.lib.Common import seconds_to_nice, get_player_map,get_player_name
from herotools.important_times import ImportantTimes, MAIN_TIME
from StaticAnalysis.analysis.visualisation import make_image_annotation_flex, make_image_annotation, make_image_annotation_table
from itertools import cycle
from herotools.HeroTools import HeroIconPrefix, HeroIDType, convertName, heroShortName
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from math import ceil, floor
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm.query import Query
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import io
import numpy as np

og_id = 2586976
entity = 8605863
psg = 15
team_id = og_id
time = MAIN_TIME
time = ImportantTimes['Patch_7_34']
team: TeamInfo = db.get_team(team_id)
r_query = team.get_replays(db.session).filter(Replay.endTimeUTC >= time)

q_test = (db.session.query(PickBans)
                    .filter(PickBans.is_pick == True)
                    .filter(PickBans.teamID == team_id)
                    .join(r_query.subquery()))

from sqlalchemy import or_
first_selection = (
    db.session.query(TeamSelections)
      .filter(team.custom_filter(TeamSelections.teamID, TeamSelections.stackID))
      .filter(TeamSelections.firstPick == True)
      .join(r_query.subquery())
)
second_selection = (
    db.session.query(TeamSelections)
      .filter(team.custom_filter(TeamSelections.teamID, TeamSelections.stackID))
      .filter(TeamSelections.firstPick == False)
      .join(r_query.subquery())
)
from sqlalchemy.orm import contains_eager
from sqlalchemy import and_
# second_selection_pb = (
#     db.session.query(PickBans)
#       .join(TeamSelections, and_(TeamSelections.replay_ID == PickBans.replayID, TeamSelections.team == PickBans.team))
#       .options(contains_eager(TeamSelections.draft))
#       .filter(team.custom_filter(TeamSelections.teamID, TeamSelections.stackID))
#       .filter(TeamSelections.firstPick == False)
#       .join(r_query.subquery())
# )
fq = first_selection.subquery()
first_selection_pb = (
    db.session.query(PickBans)
      .filter(PickBans.is_pick == True)
      .join(fq, and_(fq.c.replay_ID == PickBans.replayID, fq.c.team == PickBans.team))
)
sq = second_selection.subquery()
second_selection_pb = (
    db.session.query(PickBans)
      .filter(PickBans.is_pick == True)
      .join(sq, and_(sq.c.replay_ID == PickBans.replayID, sq.c.team == PickBans.team))
)

@dataclass
class OrderTimeRegion:
    start: datetime
    first_pick: list
    second_pick: list
    end: datetime = None

picks_patch_7_34 = OrderTimeRegion(ImportantTimes['Patch_7_34'],
                                   [8, 14, 15, 18, 23],
                                   [9, 13, 16, 17, 24],
                                   None)


df = read_sql(q_test.statement, db.session.bind)
firstp_df = read_sql(first_selection_pb.statement, db.session.bind)
secondp_df = read_sql(second_selection_pb.statement, db.session.bind)

# Pick patterns that do not match
print(firstp_df[~firstp_df['order'].isin(picks_patch_7_34.first_pick)])
print(secondp_df[~secondp_df['order'].isin(picks_patch_7_34.second_pick)])


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
# firstp_df = verify_fix_order(firstp_df, picks_patch_7_34.first_pick)
# secondp_df = verify_fix_order(secondp_df, picks_patch_7_34.first_pick)

verify_fix_order(firstp_df, picks_patch_7_34.first_pick)
verify_fix_order(secondp_df, picks_patch_7_34.second_pick)

from pandas import concat
pick_df = concat([firstp_df, secondp_df], ignore_index=True)

from collections import Counter
count_df = pick_df.groupby(['playerID', 'order']).agg({'hero':Counter})
from pandas import pivot_table
# This provides a more natural representation, moving the order out to columns
rotatioed = pivot_table(pick_df, index='playerID', columns='order', values='hero', aggfunc=Counter, fill_value=Counter())

@dataclass
class ColumnDesc:
    columns: tuple
    name: str
    rel_width: float


DIVIDER = object()


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


def build_table(df: DataFrame, table_desc: list, team: TeamInfo) -> DataFrame:
    out_df = DataFrame()
    # Names for the first column
    out_df['Name'] = df['playerID'].apply(lambda x: get_player_name(db.team_session, x, team))

    c: ColumnDesc
    for c in table_desc:
        if c is DIVIDER:
            continue
        out_df[c.name] = df.loc[:, c.columns].sum(axis=1)

    return out_df


rotatioed = rotatioed.reset_index()
final_df = build_table(rotatioed, table_desc, team)


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

from math import ceil
def draw_cell_image(heroes: Counter, table_setup: TableProperties, width_scale: float = 1.0) -> Image:
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

test_cell = final_df.iloc[1, 1]
cell_image = draw_cell_image(test_cell, table_setup)
cell_image.save("test_cell.png")

test_cell_bigger = final_df.iloc[5, -3]
cell_image2 = draw_cell_image(test_cell_bigger, table_setup)
cell_image2.save("test_cell2.png")


def draw_name(name: str, table_setup: TableProperties) -> Image:
    font = ImageFont.truetype('arialbd.ttf', table_setup.header_font_size)
    width = (
        4 * table_setup.padding
        + int(font.getlength(name))
    )
    height = (
        2 * table_setup.padding
        + table_setup.header_font_size
    )
    # Right justified
    x_text = width - table_setup.padding
    y_text = table_setup.padding

    name_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    name_canvas = ImageDraw.Draw(name_image)

    name_canvas.text((x_text, y_text), anchor="rt",
                     font=font, fill=(0, 0, 0), align="right",
                     text=name)

    return name_image


def draw_header(title: str, table_setup: TableProperties) -> Image:
    font = ImageFont.truetype('arialbd.ttf', table_setup.header_font_size)
    width = (
        2 * table_setup.padding
        + int(font.getlength(title))
    )
    height = (
        2 * table_setup.padding
        + table_setup.header_font_size
    )
    # Right justified
    x_text = width - table_setup.padding
    y_text = table_setup.padding

    header_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    header_canvas = ImageDraw.Draw(header_image)

    header_canvas.text((x_text, y_text), anchor="rt",
                       font=font, fill=(0, 0, 0), align="right",
                       text=title)

    return header_image

@dataclass(frozen=True)
class Image_PH:
    size: (int, int) = (0, 0)
    real_image: bool = False


header_ph = Image_PH((0, 0), real_image=False)
divider = Image.new('RGBA', (table_setup.divider_spacing, table_setup.padding), (255, 255, 255, 0))
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

image_df = image_table(final_df, table_desc, table_setup)


def draw_table(image_df: DataFrame, table_setup: TableProperties):
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
        max_height = max(c.apply(lambda x: x.size[1]))
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
    for (_, row), y in zip(image_df.iloc[1:].iterrows(), col_heights[:-1]):
        for img, x in zip(row, col_widths[:-1]):
            # table_image.paste(img, (x, y), img)
            pass

    return table_image


table_image = draw_table(image_df, table_setup)
table_image.save("test_table.png")