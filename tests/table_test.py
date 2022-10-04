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
from analysis.ward_vis import colour_list
from pandas import DataFrame, Interval, IntervalIndex, cut, read_sql
from replays.Replay import Replay, Team
from lib.Common import seconds_to_nice, get_player_map,get_player_name
from lib.important_times import ImportantTimes
from analysis.visualisation import make_image_annotation_flex, make_image_annotation, make_image_annotation_table
from itertools import cycle
from lib.HeroTools import HeroIconPrefix, HeroIDType, convertName, heroShortName
import matplotlib.patches as patches

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

    def tot_height(self):
        return sum(self.players_size.values()) + self.header_size

    def tot_width(self):
        return sum(self.order_size.values())

    def _get_bottom_left(self, order: int, steam_id: int) -> Tuple[int, int]:
        # Measure from bottom left as its a graph
        x = 0
        for o in self.orders:
            if o == order:
                break
            x += self.order_size[o]

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

    hero_size = 16
    padding = 2
    summarize_after = 10
    heroes_per_row = 5
    add_other = True
    header_size = 10 + padding

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
        if self.total_heroes > self.table.summarize_after:
            if self.table.add_other:
                fixed_total = self.table.summarize_after + 1
            else:
                fixed_total = self.table.summarize_after
        else:
            fixed_total = self.total_heroes

        width = self.table.padding
        if fixed_total > self.table.heroes_per_row:
            width += self.table.hero_size * self.table.heroes_per_row
        else:
            width += self.table.hero_size * self.total_heroes
        width += self.table.padding

        height = self.table.padding
        height += self.table.hero_size +\
             (self.table.hero_size + self.table.padding)\
             * fixed_total//self.table.heroes_per_row
        height += self.table.padding

        return (width, height)

    def _get_bottom_left(self) -> Tuple[int, int]:
        return self.table._get_bottom_left(self.order, self.steam_id)

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
        for h, i in zip(self.heroes, cycle(range(5))):
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
table_test.draw(ax)
plt.show()