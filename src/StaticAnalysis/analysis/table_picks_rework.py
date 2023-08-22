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
    grouped: list


picks_patch_7_33 = OrderTimeRegion(ImportantTimes['Patch_7_33'],
                                   [5, 8, 16, 17, 23],
                                   [6, 7, 15, 18, 24],
                                   ImportantTimes['Patch_7_34'],
                                   [[5,], [6, 7], [8,]
                                    [15,], [16, 17], [18,],
                                    [23,], [24]])
picks_patch_7_34 = OrderTimeRegion(ImportantTimes['Patch_7_34'],
                                   [8, 14, 15, 18, 23],
                                   [9, 13, 16, 17, 24],
                                   None,
                                   ((8,), (9,),
                                    (13,), (14, 15), (16, 17), (18,),
                                    (23,), (24,)))


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
    pick_order: OrderTimeRegion


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
    pick_order=picks_patch_7_34,
)

# Grouping of the cells for picks
grouped_picks = (
    8, 9, 13, (14, 15), (16, 17), 18, 23, 24
)


class Cell():
    def __init__(self) -> None:
        self.heroes = {}
        self.total_heroes = 0
        self.relative_width = 1

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
        if fixed_total > preferences.heroes_per_row:  # More heroes than fit a row so max size is a row
            width = preferences.hero_size * preferences.heroes_per_row
            width += preferences.padding * preferences.heroes_per_row
        else:  # Max size is the number of heroes with padding
            width = preferences.hero_size * self.total_heroes
            width += preferences.padding * self.total_heroes

        # Height
        hero_lines = ceil(fixed_total/preferences.heroes_per_row)
        height = preferences.hero_size
        height += (preferences.hero_size + preferences.padding)*hero_lines
        if include_text:
            height += hero_lines*(preferences.padding + preferences.count_font_size)

        return (width, height)

    def draw(self, preferences: TablePreferences, add_text=True) -> Image:
        # Sort the heroes by total first
        self.heroes = {k: v for k, v in
                       sorted(self.heroes.items(), key=lambda i: i[1],
                              reverse=True)}

        width, height = self.cell_size(preferences, add_text)
        cell_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        cell_canvas = ImageDraw.Draw(cell_image)
        font = preferences.count_font
        heroes_per_row = self.table.heroes_per_row * self.relative_width

        x, y = 0, self.table.padding
        tot = 0
        for h, i in zip(self.heroes, cycle(range(heroes_per_row))):
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

            if i == heroes_per_row - 1:
                y += self.table.padding
                y += self.table.hero_size
                if add_text:
                    y += self.table.padding
                    y += self.table.hero_size
                x = 0
            tot += 1

        return cell_image


class PlayerRow():
    def __init__(self, name: str) -> None:
        self.name = name
        self.cells = {}
        self.max_height = 0

    def add_hero(self, order: int, hero: str) -> Cell:
        c: Cell
        c = self.cells.get().get(order,
                                 Cell(table=self, order=order,
                                      steam_id=self.steam_id))
        c.add_hero(hero)

    def draw_name(self, preferences: TablePreferences):
        font = preferences.header_font
        left, top, right, bottom = font.getbbox(self.name)
        width, height = right - left, bottom - top
        text_image = Image.new('RGB', (width, height), height)
        text_canvas = ImageDraw.Draw(text_image)
        text_canvas.text((0, 0), text=self.name, font=font,
                         anchor="rm", align="right", fill=(0, 0, 0))

        return text_image

    def draw(self, table: "Table", groupings=None, background=(255, 255, 255, 255)) -> Image:
        cell_images = []
        for g in groupings:
            cell: Cell
            cell = sum(x for x in g)
            cell.relative_width = len(g)

            cell_images.append(cell.draw)

        # Widths should include padding already
        width = sum(table.cell_widths)
        # Add 2*table padding to image heights
        height = max(i.size[1] for i in cell_images) + 2*(padding := table.preferences.padding)
        row_image = Image.new('RGB', (width, height), height)

        # "Curstor" for image pasting
        y = padding
        # Paste in name first, right aligned
        name = self.draw_name(table.preferences)
        x = table.cell_widths[0]
        x -= padding
        x -= name.size[0]
        row_image.paste(name, (x, y), name)

        # Now Paste in cells
        x = 0
        for w, c in zip(table.cell_widths[:-1], cell_images):
            x += w
            row_image.paste(c, (x+padding, y), c)

        return row_image

    def get_cell_images(self, table: "Table", groupings) -> List[Image]:

        cell_images = {}
        for g in groupings:
            cell: Cell
            cell = sum(self.cells(x) for x in g)
            cell.relative_width = len(g)
            cell_images[g] = cell.draw(table.preferences)

        return cell_images


class Table():
    def __init__(self, player_list: dict, preferences: TablePreferences, add_text=True) -> None:
        self.players = {k: PlayerRow(n) for k, n in player_list.items()}
        self.preferences = preferences
        self.add_text = add_text

    def import_teamselection(self, selection: TeamSelections,
                             pick_order: OrderTimeRegion = None):
        if pick_order is None:
            pick_order = self.preferences.pick_order

        # Check the times are in range for the pickorder
        t = selection.replay.endTimeUTC
        before_start = t < pick_order.start
        after_end = t >= pick_order.end if pick_order.end is not None else False
        if before_start or after_end:
            print(f"Replay {selection.replay.replayID} is out of range for pick_order")
            raise ValueError()

        picks = [x for x in selection.draft if x.is_pick]
        if selection.firstPick:
            order = pick_order.first_pick
        else:
            order = pick_order.second_pick

        for p, o in zip(picks, order):
            if p.playerID not in self.players:
                continue
            self.players[p.playerID].add_hero(p.hero, o)

    def draw_order_labels(self, groupings):
        def _process(t: tuple):
            match len(t):
                case 1:
                    return f"{t[0]}"
                case 2:
                    return f"{t[0] and t[1]}"
                case 3:
                    return "".join(f"{x}, " for x in t[:-1]) + f"and {t[:-1]}"

        def _draw_text(t: str):
            font = self.preferences.header_font
            left, top, right, bottom = font.getbbox(t)
            width, height = right - left, bottom - top
            text_image = Image.new('RGB', (width, height), height)
            text_canvas = ImageDraw.Draw(text_image)
            text_canvas.text((0, 0), text=t, font=font,
                             anchor="rm", align="right", fill=(0, 0, 0))

            return text_image

        label_images = []
        for g in groupings:
            text = _process(g)
            text_image = _draw_text(text)
            label_images.append(text_image)

        return label_images

    def draw(self, groupings=None):
        if groupings is None:
            groupings = self.preferences.pick_order.grouped
        pad = self.preferences.padding

        # Order labels for the header
        label_images = self.draw_order_labels(groupings)
        # max_label_width = max(x.size[0] for x in label_images) + 2 * pad
        col_width = {k: i.size[0] + 2 * pad for k, i in zip(groupings, label_images)}
        max_label_height = max(x.size[1] for x in label_images) + 2 * pad
        cells = {}
        # Max width of each row, add player name later
        col_width = {k: 0 for k in groupings}
        # Max height for the specific player
        row_height = {k: 0 for k in self.players}
        # Also get names
        names = {}
        col_name_width = 0
        for p, row in self.players.items():
            cells[p] = (r_c := row.get_cell_images(self, groupings))
            # Keep track of the maximums for table layout, add padding here!
            row_height[p] = max(c.size[1] + 2 * pad for c in r_c)
            for g in groupings:
                col_width[g] = max(col_width[g], r_c[g].size[0] + 2 * pad)

            # Get the name, check its width, height
            names[p] = row.draw_name(self.preferences)
            col_name_width = max(col_name_width, names[p].size[0] + 2 * pad)
            row_height[p] = max(row_height[p], names[p].size[1] + 2 * pad)

        width = col_name_width + sum(x for x in col_width.values())
        height = sum(x for x in row_height.values()) + max_label_height
        # Draw the table Image, paste in cells
        table_image = Image.new('RGBA', (width, height), (255,255,255,255))
        table_canvas = ImageDraw.Draw(table_image)

        # Draw in labels, skip first cell as it is names
        x, y = col_name_width, pad
        la: ImageDraw
        for la, w in zip(label_images, col_width.values()):
            x += w
            # Left align the x
            x0 = x - pad - l.size[0]
            table_image.paste(l, (x0, y), l)

        # Draw in rows
        row_bg_cycle = ((255, 255, 255, 255), (220, 220, 220, 255))
        # Header line
        y0, y1 = max_label_height, max_label_height
        x0, x1 = 0, width
        table_canvas.line([x0, y0, x1, y1], (0, 0, 0, 255))
        # Stripes
        for h, bg in zip(row_height.values(), row_bg_cycle):
            y1 += h
            table_canvas.rectangle([x0, y0, x1, y1], fill=bg)
            y0 += h
        # Draw in objects
        x, y = col_name_width, max_label_height + pad
        for (p, c), bg in zip(cells.items(), cycle(row_bg_cycle)):
            # Name
            pass



