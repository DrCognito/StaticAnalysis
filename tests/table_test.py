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

og_id = 2586976
time = ImportantTimes['Patch_7_32']
team = db.get_team(2586976)
r_query = team.get_replays(db.session).filter(Replay.endTimeUTC >= time)
q_test = db.session.query(PickBans.hero, PickBans.order, PickBans.playerID).\
                    filter(PickBans.is_pick == True).\
                    filter(PickBans.teamID == og_id).\
                    join(db.r_query.subquery())

test_frame = read_sql(q_test.statement, db.session.bind)
# PickBans.playerID appears as anon_1
test_frame.columns = ['hero', 'order', 'steam_id']

player_list = [{x.player_id: x.name} for x in team.players]


class Table():
    def __init__(self, player_list: dict) -> None:
        self.player_list = player_list
        self.cell_table = {x: dict() for y in player_list for x in y}
        self.orders = []
        self.order_size = {}
        self.players_size = {}

    def tot_height(self):
        return sum(self.players_size.values())

    def tot_width(self):
        return sum(self.order_size.values())

    def _get_bottom_left(order: int, steam_id: int) -> Tuple[int, int]:
        return 0, 0

    def add_order(self, order: int):
        self.orders.append(order)
        self.orders.sort()

    hero_size = 5
    padding = 2
    summarize_after = 10
    heroes_per_row = 5
    add_other = True

    def add_hero(self, hero, order, steam_id):
        if steam_id not in self.cell_table:
            print(f"Missing {steam_id}")
            return
        cell = self.cell_table[steam_id].get(order, Cell(table=self))
        cell.add_hero(hero)
        self.cell_table[steam_id][order] = cell

        if order not in self.orders:
            self.add_order(order)
        width, height = cell.cell_size()
        current_width = self.order_size.get(order, 0)
        current_height = self.players_size(steam_id, 0)
        self.order_size[order] = max(current_width, width)
        self.players_size[steam_id] = max(current_height, height)


class Cell():
    def __init__(self, *, table: "Table") -> None:
        self.table = table
        self.heroes = {}
        self.total_heroes = 0

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


table_test = Table(player_list)
for h in q_test:
    table_test.add_hero(*h)