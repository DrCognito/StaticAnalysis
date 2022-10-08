import io
from dataclasses import dataclass
from datetime import datetime
from itertools import cycle
from math import ceil
from typing import Tuple

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import seaborn as sns
from lib.HeroTools import HeroIconPrefix, HeroIDType, convertName
from lib.important_times import ImportantTimes
from pandas import DataFrame
from PIL import Image, ImageDraw, ImageFont
from lib.team_info import TeamInfo
from replays.Replay import Replay
from replays.TeamSelections import TeamSelections
from sqlalchemy.orm.query import Query
from sqlalchemy.orm import Session

from analysis.visualisation import make_image_annotation_table


@dataclass
class OrderTimeRegion:
    start: datetime
    first_pick: list
    second_pick: list
    end: datetime = None


class Table():
    def __init__(self, player_list: dict, add_text=True) -> None:
        self.player_list = player_list
        self.cell_table = {x: dict() for x in player_list}
        self.orders = []
        self.order_size = {}
        self.players_size = {}
        self.order_bounds = []
        self.order_positions = set()
        self.double_positions = set()
        self.add_text = add_text
        self.min_for_text = 2

    def add_teamselection(self, selection: TeamSelections, fix_order=True):
        if fix_order:
            for order in self.pick_orders:
                # print(order)
                t = selection.replay.endTimeUTC
                match_start = t >= order.start
                if order.end:
                    match_end = t < order.end
                else:
                    match_end = True
                # print(f"{match_start} {match_end}, {t}")
                if match_start and match_end:
                    first_pick = order.first_pick
                    second_pick = order.second_pick
                    if not self.orders:
                        for i in first_pick + second_pick:
                            self.add_order(i)
                    break

        if selection.firstPick:
            order = first_pick
        else:
            order = second_pick

        picks = [x for x in selection.draft if x.is_pick]
        for p, fixedo in zip(picks, order):
            if p.playerID not in self.player_list:
                continue
            if fix_order:
                self.add_hero(p.hero, fixedo, p.playerID)
            else:
                self.add_hero(p.hero, p.order, p.playerID)

    def tot_height(self):
        return sum(self.players_size.values()) + self.header_size

    def tot_width(self):
        return sum(self.order_size.values()) + (self.double_line_space)*len(self.order_bounds) + len(self.orders)

    def _calc_order_bound(self):
        self.order_bounds = []
        for first, second in zip(self.orders[:-1], self.orders[1:]):
            if second - first > 1:
                # print(f"{second}, {first}")
                self.order_bounds.append(second)

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
    summarize_after = 150
    heroes_per_row = 5
    add_other = True
    header_size = 22
    header_font_size = header_size - padding
    count_font_size = 16
    double_line_space = 5
    pick_orders = [
        OrderTimeRegion(ImportantTimes['Patch_7_32'],
                        [5, 8, 16, 17, 23],
                        [6, 7, 15, 18, 24],
                        None)
    ]

    def get_dataframe(self, as_percent) -> DataFrame:
        phases = ["1st Phase", "2nd Phase", "3rd Phase", "4th Phase"]
        columns = []
        bounds = {}
        accumulating = []
        for o in self.orders:
            if o in self.order_bounds:
                name = phases.pop(0)
                bounds[name] = accumulating
                accumulating = []
                columns.append(name)
            columns.append(o)
            accumulating.append(o)
        bounds["Final Phase"] = accumulating
        columns.append("Final Phase")
        df = DataFrame(columns=columns)
        for p in self.cell_table:
            counts = {x[0]:x[1].total_heroes for x in self.cell_table[p].items()}
            df.loc[self.player_list[p]] = counts
        # Missing orders will NaN
        df = df.fillna(0)
        # print(df)
        if as_percent:
            df[self.orders] = df[self.orders].div(df[self.orders].sum(axis=1), axis=0).multiply(100)
            df = df.round(0)
        for column, bound in bounds.items():
            print(column)
            df[column] = df[bound].sum(axis=1)

        return df

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
            print(f"{hero} {order} {steam_id}::{self.player_list[steam_id]}")
            self.order_size[order] = 0
            # self.order_size = dict(sorted(self.order_size.items()))
            self.add_order(order)
        width, height = cell.cell_size(include_text=self.add_text)
        # Minimum should be the hero width
        min_width = (self.hero_size+self.padding)*self.heroes_per_row+self.padding
        current_width = self.order_size.get(order, min_width)
        # Minimum should be the player font size
        current_height = self.players_size.get(steam_id, self.header_font_size)
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
        c: Cell
        cells = []
        for o in self.orders:
            c = self.cell_table[steam_id].get(o, None)
            if c is not None:
                cell_image = c.draw_cell_image(add_text=self.add_text)
                cells.append(cell_image)
            else:
                # Add spacer
                spacer = Image.new('RGBA', (self.order_size[o], height), background)
                cells.append(spacer)

        height = self.players_size[steam_id]
        # Sum all the cells
        # width = sum(x.cell_size()[0] for x in table_test.cell_table[steam_id].values())
        width = sum(x.size[0] for x in cells)
        # Add single lines
        width += len(self.orders)
        # Add double lines
        width += self.double_line_space*len(self.order_bounds)
        row_image = Image.new('RGBA', (width, height), background)
        added_lines = ImageDraw.Draw(row_image)
        x, y = 0, 0
        added_lines.line([(x, 0), (x, height)], fill='black', width=1)
        # self.order_positions.add(x)
        x += 1
        c: Image
        for o, c in zip(self.orders, cells):
            if o in self.order_bounds:
                x += self.double_line_space
                row_image.paste(c, (x, y), c)
                added_lines.line([(x, 0), (x, height)], fill='black', width=1)
                self.double_positions.add(x)
            else:
                row_image.paste(c, (x, y), c)
            x += c.size[0]
            added_lines.line([(x, 0), (x, height)], fill='black', width=1)
            self.order_positions.add(x)
            x += 1

        return row_image

    def draw_table_image(self):
        height = self.tot_height()
        width = self.tot_width()

        player_names = self.draw_player_names()
        width += player_names.size[0]

        row_bg_cycle = [(255, 255, 255, 255), (220, 220, 220, 255)]
        x, y = player_names.size[0], self.header_size
        rows = []
        for p, rbg in zip(self.player_list, cycle(row_bg_cycle)):
            row_image = self.draw_row_image(p, rbg)
            # table_image.paste(row_image, (x, y), row_image)
            rows.append((row_image, (x, y)))
            y += self.players_size[p]
        order_labels = self.draw_order_labels()

        table_image = Image.new('RGBA', (width, height), (255,255,255,255))
        table_image.paste(player_names, (0, self.header_size), player_names)
        table_image.paste(order_labels, (player_names.size[0], 0), order_labels)
        for img, pos in rows:
            table_image.paste(img, pos, img)
        table_canvas = ImageDraw.Draw(table_image)
        table_canvas.line([(0, self.header_size), (table_image.size[0], self.header_size)],
                          fill='black', width=1)
        return table_image

    def draw_player_names(self):
        font = ImageFont.truetype('arialbd.ttf', self.header_font_size)
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
        font = ImageFont.truetype('arialbd.ttf', self.header_font_size)
        height = self.header_size
        width = self.tot_width()

        text_image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
        text_canvas = ImageDraw.Draw(text_image)
        text_canvas.line([(0, 0), (0, self.header_size)],
                         fill='black', width=1)
        # total = 0
        positions = sorted(self.order_positions)
        for o, pos in zip(self.orders, positions):
            # total += self.order_size[o]
            x = pos - self.padding
            y = self.header_size - self.padding
            # if o in self.order_bounds:
            #     adj_x = total - self.double_line_space
            #     text_canvas.line([(adj_x, 0), (adj_x, self.header_size)],
            #                      fill='black', width=1)
            #     text_canvas.text((adj_x, y), text=str(o), font=font,
            #                      anchor="rb", fill=(0, 0, 0))
            # else:
            text_canvas.text((x, y), text=str(o), font=font,
                            anchor="rb", fill=(0, 0, 0))
            text_canvas.line([(pos, 0), (pos, self.header_size)],
                            fill='black', width=1)

        for pos in sorted(self.double_positions):
            text_canvas.line([(pos, 0), (pos, self.header_size)],
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

    def cell_size(self, include_text=True) -> Tuple[int, int]:
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

        hero_lines = ceil(fixed_total/self.table.heroes_per_row)
        height = self.table.padding
        height += self.table.hero_size +\
             (self.table.hero_size + self.table.padding)\
             * hero_lines
        height += self.table.padding
        if include_text:
            height += hero_lines*(self.table.padding + self.table.count_font_size)

        return (width, height)

    def _get_bottom_left(self) -> Tuple[int, int]:
        return self.table._get_bottom_left(self.order, self.steam_id)

    def draw_cell_image(self, add_text=True) -> Image:
        # Sort the heroes by total first
        self.heroes = { k: v for k, v in
                        sorted(self.heroes.items(), key=lambda i: i[1],
                               reverse=True)}
        height = self.table.players_size[self.steam_id]
        width = self.table.order_size[self.order]
        cell_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        cell_canvas = ImageDraw.Draw(cell_image)
        font = ImageFont.truetype('arialbd.ttf', self.table.count_font_size)
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

    def total_heroes(self) -> int:
        return sum(self.heroes.values())


def create_tables(r_query: Query, session: Session, team: TeamInfo,
                  add_text=True) -> Image:
    id_query = r_query.with_entities(Replay.replayID)
    selection = (session.query(TeamSelections)
                        .filter(TeamSelections.replay_ID.in_(id_query)))
    player_list = {x.player_id: x.name for x in team.players}
    pick_table = Table(player_list, add_text=add_text)
    for team in selection:
        pick_table.add_teamselection(team)

    table_image = pick_table.draw_table_image()

    df = pick_table.get_dataframe(as_percent=True)
    # Seaborn heatmap
    # summary_table = seaborn_heatmap(df)
    # image
    # Nicer number rounding and formatting
    df = df.round(0).astype(str).replace(r'\.0$', '%', regex=True)
    avg_cell_width = table_image.size[0]//(len(df.columns)+3)
    summary_table = render_percent_table(df, min_width=avg_cell_width)

    spacing = 50
    width = max(summary_table.size[0], table_image.size[0])
    height = summary_table.size[1] + table_image.size[1] + spacing
    final = Image.new('RGBA', (width, height),
                      (255, 255, 255, 255))
    x, y = 0, 0
    final.paste(table_image, (x, y), table_image)
    y += table_image.size[1] + spacing
    final.paste(summary_table, (x, y), summary_table)

    return final


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
            font = header_font if n == 'Index' else text_font
            text = str(t)
            length = ceil(font.getlength(text)) + 2*padding
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


def seaborn_heatmap(df: DataFrame, fig=None, cmap="YlGnBu") -> Image:
    if fig is None:
        fig = plt.figure()

    sns.heatmap(df, annot=True, cmap="YlGnBu", cbar=True)

    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    image = Image.open(img_buf)

    return image
