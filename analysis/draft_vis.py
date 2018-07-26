from PIL import Image, ImageDraw, ImageFont
import math
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.HeroTools import convertName, HeroIDType, HeroIconPrefix
from replays.TeamSelections import TeamSelections
from replays.Replay import Replay, Team
from typing import List


def pickban_box_image(size=(64, 80), isPick=True, isWinner=False):
    '''Template for the pick and ban box'''

    text = "PICK" if isPick else "BAN"
    outline_colour = (0, 255, 0, 255) if isPick else (255, 0, 0, 255)
    background_colour = (255, 255, 0, 0) if isWinner else (255, 255, 255, 0)

    out_box = Image.new('RGBA', size, background_colour)
    canvas = ImageDraw.Draw(out_box)

    # Background boxes
    # [(x0, y0), (x1, y1)]
    canvas.rectangle([(0, 0), (size[0]-1, size[0])],
                     fill=None, outline=outline_colour)
    # The pick or ban box is positioned assuming a square main icon box!
    canvas.rectangle([(0, size[0]+1), (size[0], size[1])],
                     fill="black")

    # Text
    font_size = size[1] - size[0]
    font = ImageFont.truetype('arialbd.ttf', font_size)
    x_pos = math.floor(size[0]/2 - font.getsize(text)[0]/2)
    canvas.text((x_pos, size[0]), text, fill=outline_colour,
                font=font)

    return out_box


def hero_box_image(hero, isPick, isFirst=False, isWinner=False):
    # Get the template box.
    hero_box = pickban_box_image(isPick=isPick, isWinner=isWinner)

    # Get and resize the hero icon.
    icon_location = HeroIconPrefix / convertName(hero, HeroIDType.NPC_NAME,
                                                 HeroIDType.ICON_FILENAME)

    icon = Image.open(icon_location)
    icon = icon.resize((64, 64))

    # Paste the icon into the box
    hero_box.paste(icon, (0, 0), icon)

    # If its the first pick we want to highlight with a triangle.
    if isFirst:
        size = hero_box.size
        canvas = ImageDraw.Draw(hero_box)

        halfPoint = math.floor((size[1]-size[0])/2)
        spacing = 0
        # Draws in the yellow triangle
        canvas.polygon([(1+spacing, size[0]+1+spacing),
                        (halfPoint+spacing, size[0]+halfPoint+spacing),
                        (1+spacing, size[1]-1+spacing)],
                       fill='yellow')

    return hero_box


def pickban_line_image(replay: Replay, main_side: Team, spacing=5):
    def _process_team(team: TeamSelections):
        hero_boxes = []
        tot_width = spacing
        team_win = team.team == replay.winner
        for selection in team.draft:
            draw_first = selection.order == 0 and team.firstPick

            hbox = hero_box_image(selection.hero,
                                  selection.is_pick,
                                  draw_first,
                                  team_win)
            tot_width += hbox.size[0] + spacing
            height = hbox.size[1] + spacing*2
            hero_boxes.append(hbox)

        b_colour = (255, 255, 0, 255) if team_win else (255, 255, 255, 0)
        out_box = Image.new('RGBA', (tot_width, height), b_colour)

        processed_size = spacing
        for i, hbox in enumerate(hero_boxes):
            # Initial offset starts after the border (+spacing)
            x_off = processed_size + i*spacing
            out_box.paste(hbox,
                          (x_off, spacing),
                          hbox)
            processed_size += hbox.size[0]

        return out_box

    for t in replay.teams:
        if len(t.draft) == 0:
            print("Failed to get draft for {} in replay {}".format(str(t.team), t.replay_ID))
            return None
        if t.team == main_side:
            team_line = _process_team(t)
        else:
            opposition_line = _process_team(t)

    spacer = Image.new('RGBA', (10, team_line.size[1]), (255,255,255,0))
    spacerDraw = ImageDraw.Draw(spacer)
    spacerDraw.line([(0,0),(0,team_line.size[1])], fill='black', width=2*spacing)

    width = team_line.size[0] + spacer.size[0] + opposition_line.size[0]
    height = team_line.size[1]
    out_box = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    out_box.paste(team_line, (0, 0), team_line)
    out_box.paste(spacer, (team_line.size[0], 0), spacer)
    out_box.paste(opposition_line,
                  (team_line.size[0] + spacer.size[0], 0),
                  opposition_line)

    return out_box


def replay_draft_image(replays: List[Replay], main_side: Team, team_name: str):
    lines = list()
    tot_height = 0
    max_width = 0

    # Get the lines for each replay and store so we can build our sheet
    for replay in replays:
        line = pickban_line_image(replay, main_side)
        if line is None:
            continue
        lines.append(line)
        tot_height += line.size[1]
        max_width = max(max_width, line.size[0])

    # Add them to the sheet image
    sheet = Image.new('RGBA', (max_width, tot_height), (255, 255, 255, 0))
    y_off = 0
    for line in lines:
        off_set = 0
        if line.size[0] < max_width:
            off_set = math.floor((max_width - line.size[0])/2)
        sheet.paste(line, (off_set, y_off), line)
        y_off += line.size[1]

    # Finally add a title
    font_size = 30
    final_image = Image.new('RGBA',
                            (sheet.size[0], sheet.size[1]+font_size),
                            (255, 255, 255, 0))
    canvas = ImageDraw.Draw(final_image)

    font = ImageFont.truetype('arialbd.ttf', font_size)
    left_size = font.getsize(team_name)
    right_size = font.getsize("Opponent")

    canvas.text((5, 0), team_name, fill='black', font=font)
    canvas.text((sheet.size[0]/2 + 5, 0), 'Opponent', fill='black', font=font)

    # Paste the old thing in
    final_image.paste(sheet, (0, font_size), sheet)

    return final_image
