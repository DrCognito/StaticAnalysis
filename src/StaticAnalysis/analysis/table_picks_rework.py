from dataclasses import dataclass
from datetime import datetime
from itertools import cycle
from math import ceil
from typing import Tuple, List

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


@dataclass
class TablePreferences:
    hero_size: int
    padding: int
    summarize_after: int
    heroes_per_row: int
    add_other: bool
    header_size: int
    header_font_size: int
    header_font: ImageFont
    count_font_size: int
    count_font: ImageFont
    double_line_space: 5
    pick_orders: List[OrderTimeRegion]


default_table = TablePreferences(
    hero_size=22,
    padding=2,
    summarize_after=200,
    heroes_per_row=5,
    add_other=True,
    header_size=22,
    header_font_size=20,
    header_font=ImageFont.truetype('arialbd.ttf', 20),
    count_font_size=16,
    count_font=ImageFont.truetype('arialbd.ttf', 16),
    double_line_space=5,
    pick_orders=[
                picks_patch_7_33,
                picks_patch_7_34,
    ],
)


class Cell():
    def __init__(self) -> None:
        self.heroes = {}
        self.total_heroes = 0

    def __add__(self, other: "Cell") -> "Cell":
        new_cell = Cell()
        new_cell.heroes = self.heroes
        new_cell.total_heroes = self.total_heroes

        for h, i in other.heroes.items():
            if h in new_cell.heroes:
                new_cell.heroes[h] += i
            else:
                new_cell.heroes[h] = i
                new_cell.total_heroes += 1

        return new_cell

    def add_hero(self, hero: str):
        if hero in self.heroes:
            self.heroes[hero] += 1
        else:
            self.heroes[hero] = 1
            self.total_heroes += 1

    def cell_size(self, preferences: TablePreferences, include_text=True) -> Tuple[int, int]:
        # If we are summarising limit to total heroes (+1 for other)
        if self.total_heroes >= preferences.summarize_after:
            if self.preferences.add_other:
                fixed_total = preferences.summarize_after + 1
            else:
                fixed_total = preferences.summarize_after
        else:
            fixed_total = self.total_heroes

        # Width
        # Absolute minimum width is padding
        width = preferences.padding
        if fixed_total > preferences.heroes_per_row:  # More heroes than fit a row so max size is a row
            width += preferences.hero_size * preferences.heroes_per_row
            width += preferences.padding * preferences.heroes_per_row
        else:  # Max size is the number of heroes with padding
            width += preferences.hero_size * self.total_heroes
            width += preferences.padding * self.total_heroes
        width += preferences.padding

        # Height
        hero_lines = ceil(fixed_total/preferences.heroes_per_row)
        height = preferences.padding
        height += preferences.hero_size
        height += (preferences.hero_size + preferences.padding)*hero_lines
        height += preferences.padding
        if include_text:
            height += hero_lines*(preferences.padding + preferences.count_font_size)

        return (width, height)

    def draw(self, preferences: TablePreferences,  add_text=True) -> Image:
        # Sort the heroes by total first
        self.heroes = {k: v for k, v in
                       sorted(self.heroes.items(), key=lambda i: i[1],
                              reverse=True)}

        width, height = self.cell_size(preferences, add_text)
        cell_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        cell_canvas = ImageDraw.Draw(cell_image)
        font = preferences.count_font

        x, y = 0, self.table.padding
        tot = 0
        for h, i in zip(self.heroes, cycle(range(self.table.heroes_per_row))):
            if tot >= self.table.summarize_after:
                if self.table.add_other:
                    pass
                break

            x += self.table.padding
            try:
                # Get and resize the hero icon.
                icon = HeroIconPrefix / convertName(h, HeroIDType.NPC_NAME,
                                                    HeroIDType.ICON_FILENAME)
            except (ValueError, KeyError):
                print("Unable to find hero icon for (table): " + h)
                continue
            h_icon = Image.open(icon)
            h_icon = h_icon.resize((self.table.hero_size, self.table.hero_size))
            # Add icon
            cell_image.paste(h_icon, (x, y))

            # Add the text count if were counting!
            if add_text and self.heroes[h] >= self.table.min_for_text:
                adj_y = y + self.table.padding + self.table.hero_size
                adj_x = x + self.table.hero_size//2
                text = str(self.heroes[h])
                cell_canvas.text((adj_x, adj_y), text=text, font=font,
                                 anchor="mt", align="right", fill=(0, 0, 0))
            x += self.table.hero_size

            if i == self.table.heroes_per_row - 1:
                y += self.table.padding
                y += self.table.hero_size
                if add_text:
                    y += self.table.padding
                    y += self.table.hero_size
                x = 0
            tot += 1

        return cell_image


class PlayerRow():
    pass


class Table():
    pass
