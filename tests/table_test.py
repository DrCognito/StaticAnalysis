from email.mime import base
import os
import sys
from typing import Tuple
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.minimal_db as db
from replays.Player import Player
from replays.TeamSelections import PickBans, TeamSelections

from lib.team_info import TeamInfo

import matplotlib.pyplot as plt

from os import environ as environment
from dotenv import load_dotenv
from analysis.ward_vis import colour_list, plot_labels
from pandas import DataFrame, Interval, IntervalIndex, cut, read_sql
from replays.Replay import Replay, Team
from lib.Common import seconds_to_nice, get_player_map,get_player_name
from lib.important_times import ImportantTimes
from analysis.visualisation import make_image_annotation_flex, make_image_annotation, make_image_annotation_table
from itertools import cycle
from lib.HeroTools import HeroIconPrefix, HeroIDType, convertName, heroShortName
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont

og_id = 2586976
entity = 8605863
psg = 15
team_id = psg
time = ImportantTimes['Patch_7_32']
team = db.get_team(team_id)
r_query = team.get_replays(db.session).filter(Replay.endTimeUTC >= time)
q_test = db.session.query(PickBans.hero, PickBans.order, PickBans.playerID).\
                    filter(PickBans.is_pick == True).\
                    filter(PickBans.teamID == team_id).\
                    join(db.r_query.subquery())

test_frame = read_sql(q_test.statement, db.session.bind)
# PickBans.playerID appears as anon_1
test_frame.columns = ['hero', 'order', 'steam_id']

# player_list = [{x.player_id: x.name} for x in team.players]
player_list = {x.player_id: x.name for x in team.players}


class Table():
    def __init__(self, player_list: dict) -> None:
        self.player_list = player_list
        self.cell_table = {x: dict() for x in player_list}
        self.orders = []
        self.order_size = {}
        self.players_size = {}
        self.order_bounds = []

    def tot_height(self):
        return sum(self.players_size.values()) + self.header_size

    def tot_width(self):
        return sum(self.order_size.values()) + (self.double_line_space)*len(self.order_bounds)

    def _calc_order_bound(self):
        for o in self.order_bounds:
            self.order_size[o] -= self.double_line_space
        self.order_bounds = []
        for first, second in zip(self.orders[:-1], self.orders[1:]):
            if second - first > 1:
                # print(f"{second}, {first}")
                self.order_bounds.append(second)
                self.order_size[first] += self.double_line_space

    def _get_bottom_left(self, order: int, steam_id: int) -> Tuple[int, int]:
        # Measure from bottom left as its a graph
        x = 0
        for o in self.orders:
            if o == order:
                break
            x += self.order_size[o]

        # Add double lines for bounds
        extra_bounding_space = 0
        for i in self.orders:
            if i in self.order_bounds:
                extra_bounding_space += self.double_line_space
            if i == o:
                break
        x += extra_bounding_space

        # Start from top of table
        y = self.header_size
        for p in self.player_list:
            y += self.players_size[p]
            if p == steam_id:
                break
        y = self.tot_height() - y

        return x, y

    def add_order(self, order: int):
        self.orders.append(order)
        self.orders.sort()
        self._calc_order_bound()

    hero_size = 22
    padding = 2
    summarize_after = 50
    heroes_per_row = 5
    add_other = True
    header_size = 22
    font_size = header_size - padding
    double_line_space = 5

    def add_hero(self, hero, order, steam_id):
        if steam_id not in self.cell_table:
            # print(f"Missing {steam_id}")
            return
        cell = self.cell_table[steam_id].get(order,
                                             Cell(table=self, order=order,
                                                  steam_id=steam_id))
        cell.add_hero(hero)
        self.cell_table[steam_id][order] = cell

        if order not in self.orders:
            print(f"{hero} {order} {steam_id}")
            self.order_size[order] = 0
            self.order_size = dict(sorted(self.order_size.items()))
            self.add_order(order)
        width, height = cell.cell_size()
        current_width = self.order_size.get(order, 0)
        current_height = self.players_size.get(steam_id, 0)
        self.order_size[order] = max(current_width, width)
        self.players_size[steam_id] = max(current_height, height)

    def highlight_row(self, axe, steam_id, colour):
        x, y = self._get_bottom_left(self.orders[0], steam_id)
        print(f"Rect at {x}, {y}")
        rect = patches.Rectangle(
                                (x, y),  # bottom left starting position (x,y)
                                self.tot_width() + 0.5,  # width
                                self.players_size[steam_id],  # height
                                ec='none',
                                fc=colour,
                                alpha=.2,
                                zorder=-1
                                )
        axe.add_patch(rect)

    def add_order_text(self, axe):
        tot_w = 0
        y = self.tot_height() - self.header_size
        for o in self.orders:
            tot_w += self.order_size[o]
            axe.text(x=tot_w - self.padding, y = y, s=o, va="bottom", ha="right" )

    def add_name_text(self, axe):
        o = self.orders[0]
        for p in self.player_list:
            _, y = self._get_bottom_left(o, p)
            y += self.players_size[p] * 0.5
            axe.text(x=1-self.padding, y=y, s=self.player_list[p], va="center", ha="right")

    def draw_row_image(self, steam_id, background=(255, 255, 255, 255)):
        height = self.players_size[steam_id]
        width = self.tot_width()
        row_image = Image.new('RGBA', (width, height), background)
        added_lines = ImageDraw.Draw(row_image)
        x, y = 0, 0
        c: Cell
        for o in self.orders:
            c = self.cell_table[steam_id].get(o, None)
            if c is not None:
                cell_image = c.draw_cell_image()
                row_image.paste(cell_image, (x, y), cell_image)
            cell_width = self.order_size[o]
            added_lines.line([(x, 0), (x, height)], fill='black', width=1)
            if o in self.order_bounds:
                adj_x = x - self.double_line_space
                added_lines.line([(adj_x, 0), (adj_x, height)], fill='black', width=1)
                x += self.double_line_space
            # else:
            #     added_lines.line([(x, 0), (x, height)], fill='black', width=1)
            x += cell_width
        added_lines.line([(x, 0), (x, height)], fill='black', width=1)

        return row_image

    def draw_table_image(self):
        height = self.tot_height()
        width = self.tot_width()

        player_names = self.draw_player_names()
        width += player_names.size[0]
        order_labels = self.draw_order_labels()

        table_image = Image.new('RGBA', (width, height), (255,255,255,255))
        table_image.paste(player_names, (0, self.header_size), player_names)
        table_image.paste(order_labels, (player_names.size[0], 0), order_labels)

        row_bg_cycle = [(255, 255, 255, 255), (128, 128, 128, 255)]
        x, y = player_names.size[0], self.header_size
        for p, rbg in zip(self.player_list, cycle(row_bg_cycle)):
            row_image = self.draw_row_image(p, rbg)
            table_image.paste(row_image, (x, y), row_image)
            y += self.players_size[p]

        table_canvas = ImageDraw.Draw(table_image)
        table_canvas.line([(0, self.header_size), (table_image.size[0], self.header_size)],
                          fill='black', width=1)
        return table_image

    def draw_player_names(self):
        font = ImageFont.truetype('arialbd.ttf', self.font_size)
        width = 0
        for name in player_list.values():
            width = max(width, int(font.getlength(name)))
        width += 4*self.padding
        text_image = Image.new('RGBA', (width, self.tot_height()), (255, 255, 255, 255))
        text_canvas = ImageDraw.Draw(text_image)
        total = 0
        for p in player_list:
            text = player_list[p]
            x = width - 2*self.padding
            y = total + int(self.players_size[p]/2)
            print(f"{x}, {y}::{text}")
            text_canvas.text((x, y), text=text, font=font,
                             anchor="rm", align="right", fill=(0, 0, 0))
            total += self.players_size[p]

        return text_image

    def draw_order_labels(self):
        font = ImageFont.truetype('arialbd.ttf', self.font_size)
        height = self.header_size
        width = self.tot_width()

        text_image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
        text_canvas = ImageDraw.Draw(text_image)
        text_canvas.line([(0, 0), (0, self.header_size)],
                         fill='black', width=1)
        total = 0
        for o in self.orders:
            total += self.order_size[o]
            x = total - self.padding
            y = self.header_size - self.padding
            if o in self.order_bounds:
                adj_x = total - self.double_line_space
                text_canvas.line([(adj_x, 0), (adj_x, self.header_size)],
                                 fill='black', width=1)
                text_canvas.text((adj_x, y), text=str(o), font=font,
                                 anchor="rb", fill=(0, 0, 0))
            else:
                text_canvas.text((x, y), text=str(o), font=font,
                                anchor="rb", fill=(0, 0, 0))
            text_canvas.line([(total, 0), (total, self.header_size)],
                            fill='black', width=1)

        return text_image

    def draw(self, axe):
        axe.axis('off')
        self.add_order_text(axe)
        self.add_name_text(axe)
        for p, highlight in zip(player_list, cycle([False, True])):
            if highlight:
            # if True:
                self.highlight_row(axe, p, "grey")
        tot_h = self.header_size
        axe.plot(
                [-1, self.tot_width() + 1],
                [self.tot_height() - tot_h, self.tot_height() - tot_h],
                ls=':',
                lw='.5',
                c='grey'
            )
        # Row Lines
        for h in self.players_size.values():
            tot_h += h
            y = self.tot_height() - tot_h
            print(f"Line at {y}")
            axe.plot(
                [-1, self.tot_width() + 1],
                [y, y],
                ls=':',
                lw='.5',
                c='grey'
            )
        # Column lines
        print(self.order_size)
        axe.plot(
                [0, 0],
                [0, self.tot_height() + .5],
                ls=':',
                lw='.5',
                c='grey'
            )
        tot_w = 0
        for w in self.order_size.values():
            tot_w += w
            axe.plot(
                [tot_w, tot_w],
                [0, self.tot_height() + .5],
                ls=':',
                lw='.5',
                c='grey'
            )

        for player in self.cell_table:
            for order in self.cell_table[player]:
                self.cell_table[player][order].draw_cell(axe)


class Cell():
    def __init__(self, *, table: "Table", order, steam_id) -> None:
        self.table = table
        self.heroes = {}
        self.total_heroes = 0
        self.order = order
        self.steam_id = steam_id

    def __str__(self) -> str:
        return f"{self.steam_id}::{self.table.player_list[self.steam_id]} at {self.order}"

    def __repr__(self) -> str:
        return self.__str__()

    def add_hero(self, hero: str):
        if hero in self.heroes:
            self.heroes[hero] += 1
        else:
            self.heroes[hero] = 1
            self.total_heroes += 1

    def cell_size(self) -> Tuple[int, int]:
        if self.total_heroes >= self.table.summarize_after:
            if self.table.add_other:
                fixed_total = self.table.summarize_after + 1
            else:
                fixed_total = self.table.summarize_after
        else:
            fixed_total = self.total_heroes

        width = self.table.padding
        if fixed_total > self.table.heroes_per_row:
            width += self.table.hero_size * self.table.heroes_per_row
            width += self.table.padding * self.table.heroes_per_row
        else:
            width += self.table.hero_size * self.total_heroes
            width += self.table.padding * self.total_heroes
        width += self.table.padding

        height = self.table.padding
        height += self.table.hero_size +\
             (self.table.hero_size + self.table.padding)\
             * fixed_total//self.table.heroes_per_row
        height += self.table.padding

        return (width, height)

    def _get_bottom_left(self) -> Tuple[int, int]:
        return self.table._get_bottom_left(self.order, self.steam_id)

    def draw_cell_image(self) -> Image:
        height = self.table.players_size[self.steam_id]
        width = self.table.order_size[self.order]
        cell_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        # cell_canv = ImageDraw.Draw(cell_image)
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
            # cell_image.paste(h_icon, (x, y), h_icon)
            cell_image.paste(h_icon, (x, y))
            x += self.table.hero_size

            if i == self.table.heroes_per_row - 1:
                y += self.table.padding
                y += self.table.hero_size
                x = 0
            tot += 1

        return cell_image

    def draw_cell(self, axe):
        base_x, y = self._get_bottom_left()
        height = self.table.players_size[self.steam_id]
        # Start top left
        x = base_x
        y += height
        # Initial padding
        x += self.table.padding
        y -= self.table.padding

        tot = 0
        for h, i in zip(self.heroes, cycle(range(self.table.heroes_per_row))):
            if tot > self.table.summarize_after:
                if self.table.add_other:
                    pass
                break

            try:
                # Get and resize the hero icon.
                icon = HeroIconPrefix / convertName(h, HeroIDType.NPC_NAME,
                                                    HeroIDType.ICON_FILENAME)
            except (ValueError, KeyError):
                print("Unable to find hero icon for (table): " + h)
                continue
            # print(f"{icon}, {x}, {y}::{self.table.hero_size}, {i}")
            # make_image_annotation(icon, axe, x, y, self.table.hero_size)
            make_image_annotation_table(icon, axe, x, y, self.table.hero_size)
            # x += self.table.padding
            x += self.table.hero_size

            if i == self.table.heroes_per_row - 1:
                y -= self.table.padding
                y -= self.table.hero_size
                x = base_x + self.table.padding
            tot += 1


table_test = Table(player_list)
for h in q_test:
    table_test.add_hero(*h)
# 1000 x 300 is goal
fig, ax = plt.subplots(figsize=(20,6))
fig.set_dpi(100)
ax.set_ylim(-1, table_test.tot_height() + 1)
ax.set_xlim(0, table_test.tot_width() + .5)
# test_cell: Cell = table_test.cell_table[76561198128242457][24]
# test_cell.draw_cell(ax)
print(f"x:{table_test.tot_width()} y:{table_test.tot_height()}")
print(f"{table_test.players_size}")
# table_test.draw(ax)
# plt.show()
# cell_image = test_cell.draw_cell_image()
# row_image = table_test.draw_row_image(76561198128242457)
table_image = table_test.draw_table_image()