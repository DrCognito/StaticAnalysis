from PIL import Image, ImageDraw, ImageFont
import math
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.HeroTools import (convertName, HeroIDType, HeroIconPrefix,
                           hero_portrait, hero_portrait_prefix)
from replays.TeamSelections import TeamSelections
from replays.Replay import Replay, Team
from typing import List
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from pathlib import Path


def pickban_box_image(size=(64, 80), isPick=True, isWinner=False):
    '''Template for the pick and ban box'''

    text = "PICK" if isPick else "BAN"
    outline_colour = (0, 255, 0, 255) if isPick else (255, 0, 0, 255)
    # background_colour = (255, 255, 0, 255) if isWinner else (255, 255, 255, 255)
    background_colour = (255, 255, 255, 255)

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


def draw_firstpick_box(team: TeamSelections, size=(20, 80)):
    outline_colour = (255, 255, 255, 255)
    background_colour = (0, 0, 0, 255)

    out_box = Image.new('RGBA', size, background_colour)
    canvas = ImageDraw.Draw(out_box)

    canvas.rectangle([(0, 0), (size[0], size[1])], fill=None, outline=outline_colour)

    # Text
    if team.firstPick:
        text = "First"
        text_image = Image.new('RGBA', (size[1], size[0]), (0, 0, 0, 255))
        text_canv = ImageDraw.Draw(text_image)

        font_size = size[0]
        font = ImageFont.truetype('arialbd.ttf', font_size)
        offset = font.getsize(text)[0]
        text_canv.text(((size[1] - offset)/2, 0), text=text,
                       font=font, fill=(255, 255, 255))

        text_image = text_image.rotate(90, expand=1)
        px, py = 0, 0
        sx, sy = text_image.size
        out_box.paste(text_image, (px, py, px + sx, py + sy), text_image)

    return out_box


def hero_box_image_portrait(hero: str, is_pick: bool, pick_num: int):
    image: str = hero_portrait[hero]
    if not is_pick:
        image = image.replace(".png", "_grey.png")
    portrait_location = hero_portrait_prefix / image
    portrait = Image.open(portrait_location)

    portrait = portrait.convert("RGBA")

    # Dimensions
    dimensions = portrait.size
    text_box_x = dimensions[0]
    text_box_y = dimensions[1] // 3
    font_size = text_box_y - 2
    y_spacing = 2
    boarder = 2

    text_off_y = boarder + dimensions[1] + y_spacing

    # Build over all box
    background_colour = (255, 255, 255, 0)
    size = (text_box_x + 2*boarder,
            text_box_y + dimensions[1] + 2*boarder + y_spacing)
    out_box = Image.new('RGBA', size, background_colour)
    canvas = ImageDraw.Draw(out_box)

    if is_pick:
        text = "PICK"
        extra = hero_portrait_prefix.parent / "check_mark.png"
    else:
        text = "BAN"
        extra = hero_portrait_prefix.parent / "x_mark.png"

    extra_graphic = Image.open(extra).convert("RGBA")
    extra_graphic = extra_graphic.resize((font_size, font_size))

    # Put in the portrait
    out_box.paste(portrait, (boarder, boarder), portrait)

    # Text box
    canvas.rectangle((boarder, text_off_y,
                      boarder + text_box_x,
                      text_off_y + text_box_y), fill='black')
    font = ImageFont.truetype('arialbd.ttf', font_size)

    text_size = font.getsize(text)
    text_off = text_box_x // 2 - text_size[0] // 2 + extra_graphic.size[0] // 2
    canvas.text((text_off, text_off_y + 1), text, fill='white',
                font=font)

    # Add the extra graphic
    out_box.paste(extra_graphic, (text_off - font_size - 1, text_off_y + 2),
                  extra_graphic)

    # Number box, has to be drawn to temp canvas
    tint = (0, 0, 0, 200)
    # transparent version of the tint color.
    tmp = Image.new('RGBA', out_box.size, (0, 0, 0, 0))
    # Create a drawing context for it.
    draw = ImageDraw.Draw(tmp)
    draw.rectangle((text_box_x + boarder - 1.5*font_size,
                    boarder,
                    text_box_x,
                    boarder + 1.5*font_size),
                   fill=tint)
    str_num = str(pick_num)
    if len(str_num) == 1:
        # Adjust for single didget size manually
        factor = 1.0
    else:
        factor = 1.5
    w, h = font.getsize(str(pick_num))

    draw.text((text_box_x + boarder - factor*font_size, boarder + 1),
                str_num,
                fill='white', font=font)
    out_box = Image.alpha_composite(out_box, tmp)

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

        # Text
        text = "1st"
        font_size = size[1] - size[0]
        font = ImageFont.truetype('arialbd.ttf', font_size)
        outline_colour = (255, 255, 255, 255)
        w, h = font.getsize(text)
        x, y = (0,0)
        canvas.rectangle((x, y, x + w, y + h), fill='black')
        canvas.text((x, y), text, fill='white',
                    font=font)

    return hero_box


def add_draft_axes(draft: Image.Image, ax_in: Axes,
                   height=0.1, origin=(0, 0), origin_br=True) -> AxesImage:
    """Adds a teams draft to bottom right or top right of an image.

    Arguments:
        draft {Image.Image} -- PIL image of draft.
        ax_in {Axes} -- Target axes for plot.
        origin {(float, float)} -- Origin of image in data coordinates.

    Keyword Arguments:
        height {float} -- Scale image to this height. (default: {0.1})
        origin_br {bool} -- Image origin is bottom right.
        Top right if False. (default: {True})

    Returns:
        AxesImage -- Generated AxesImage.
    """
    img_w, img_h = draft.size
    width = height/img_h * img_w
    if origin_br:
        extent = (origin[0], origin[0] + width,
                  origin[1], origin[1] + height)
    else:
        extent = (origin[0] - width, origin[0],
                  origin[1] - height, origin[1])
    box = ax_in.imshow(draft,
                       extent=extent)

    return box


def process_team_portrait(replay: Replay, team: TeamSelections, spacing=5):
    hero_boxes = []
    tot_width = spacing

    prev_is_pick = team.draft[0].is_pick
    extra_space = []
    for selection in team.draft:
        changed_phase = prev_is_pick != selection.is_pick
        prev_is_pick = selection.is_pick
        extra_space.append(changed_phase)
        if changed_phase:
            tot_width += spacing

        hbox = hero_box_image_portrait(selection.hero,
                                       selection.is_pick,
                                       selection.order)

        tot_width += hbox.size[0]
        height = hbox.size[1] + spacing*2
        hero_boxes.append(hbox)

    tot_width += spacing
    b_colour = (255, 255, 255, 0)
    out_box = Image.new('RGBA', (tot_width, height), b_colour)

    processed_size = spacing
    extras = 0
    for i, hbox in enumerate(hero_boxes):
        # Initial offset starts after the border (+spacing)

        x_off = processed_size + extras
        # Extra if we changed our pick/ban phase
        if extra_space[i]:
            x_off += spacing
            extras += spacing
        out_box.paste(hbox,
                      (x_off, spacing),
                      hbox)
        processed_size += hbox.size[0]

    return out_box


def process_team_portrait_dotabuff(replay: Replay, team: TeamSelections, spacing=5):
    hero_boxes_pick = []
    hero_boxes_ban = []

    tot_width_pick = spacing
    tot_width_ban = spacing

    prev_is_pick = team.draft[0].is_pick
    extra_space_pick = []
    extra_space_ban = []

    height = 0
    for selection in team.draft:
        changed_phase = prev_is_pick != selection.is_pick
        prev_is_pick = selection.is_pick

        if selection.is_pick:
            extra_space_pick.append(changed_phase)
            hbox = hero_box_image_portrait(selection.hero,
                                        selection.is_pick,
                                        selection.order)
            tot_width_pick += hbox.size[0]
            hero_boxes_pick.append(hbox)
            height = max(height, hbox.size[1] + spacing*2)
        else:
            extra_space_ban.append(changed_phase)
            hbox = hero_box_image_portrait(selection.hero,
                                        selection.is_pick,
                                        selection.order)
            tot_width_ban += hbox.size[0]
            hero_boxes_ban.append(hbox)
            height = max(height, hbox.size[1] + spacing*2)

    tot_width_pick += spacing
    tot_width_ban += spacing

    #b_colour = (255, 255, 255, 0)
    b_colour = (255, 255, 255, 0)
    #out_box = Image.new('RGBA', (max([tot_width_pick, tot_width_ban]), 2*height), b_colour)
    out_box = Image.new('RGBA', (tot_width_ban, 2*height), b_colour)

    processed_size = spacing
    extras = 0
    for i, hbox in enumerate(hero_boxes_pick):
        # Initial offset starts after the border (+spacing)

        x_off = processed_size + extras
        # Extra if we changed our pick/ban phase
        if extra_space_pick[i]:
            x_off += spacing
            extras += spacing
        out_box.paste(hbox,
                      (x_off, spacing),
                      hbox)
        processed_size += hbox.size[0]

    processed_size = spacing
    extras = 0
    for i, hbox in enumerate(hero_boxes_ban):
        # Initial offset starts after the border (+spacing)

        x_off = processed_size + extras
        # Extra if we changed our pick/ban phase
        if extra_space_ban[i]:
            x_off += spacing
            extras += spacing
        out_box.paste(hbox,
                      (x_off, height),
                      hbox)
        processed_size += hbox.size[0]

    return out_box


def process_team(replay: Replay, team: TeamSelections, spacing=5):
    hero_boxes = []
    tot_width = spacing
    # First pick indicator
    pick_box = draw_firstpick_box(team)
    tot_width += pick_box.size[0]

    team_win = team.team == replay.winner
    prev_is_pick = team.draft[0].is_pick
    extra_space = []
    for selection in team.draft:
        changed_phase = prev_is_pick != selection.is_pick
        prev_is_pick = selection.is_pick
        extra_space.append(changed_phase)
        if changed_phase:
            tot_width += spacing

        draw_first = selection.order == 0 and team.firstPick

        hbox = hero_box_image(selection.hero,
                              selection.is_pick,
                              draw_first,
                              team_win)

        tot_width += hbox.size[0]
        height = hbox.size[1] + spacing*2
        hero_boxes.append(hbox)

    tot_width += spacing
    b_colour = (255, 255, 0, 255) if team_win else (255, 255, 255, 0)

    out_box = Image.new('RGBA', (tot_width, height), b_colour)

    processed_size = spacing
    out_box.paste(pick_box,
                  (spacing, spacing),
                  pick_box)
    processed_size += pick_box.size[0]
    extras = 0
    for i, hbox in enumerate(hero_boxes):
        # Initial offset starts after the border (+spacing)
        #x_off = processed_size + i*spacing + extras
        x_off = processed_size + extras
        # Extra if we changed our pick/ban phase
        if extra_space[i]:
            x_off += spacing
            extras += spacing
        out_box.paste(hbox,
                      (x_off, spacing),
                      hbox)
        processed_size += hbox.size[0]

    return out_box


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
            team_line = process_team(replay, t)
        else:
            opposition_line = process_team(replay, t)

    spacer = Image.new('RGBA', (10, team_line.size[1]), (255,255,255,0))
    spacerDraw = ImageDraw.Draw(spacer)
    spacerDraw.line([(0,0),(0,team_line.size[1])], fill='black', width=2*spacing)

    width = team_line.size[0] + spacer.size[0] + opposition_line.size[0]
    height = team_line.size[1]
    out_box = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    out_box.paste(team_line, (0, 0), team_line)
    # out_box.paste(spacer, (team_line.size[0], 0), spacer)
    out_box.paste(opposition_line,
                  (team_line.size[0] + spacer.size[0], 0),
                  opposition_line)

    return out_box


def replay_draft_image(replays: List[Replay], main_side: Team, team_name: str):
    lines = list()
    tot_height = 0
    max_width = 0
    vert_spacing = 20

    # Get the lines for each replay and store so we can build our sheet
    for replay in replays:
        line = pickban_line_image(replay, main_side)
        if line is None:
            continue
        lines.append(line)
        tot_height += line.size[1]
        tot_height += vert_spacing
        max_width = max(max_width, line.size[0])
    # Remove one to trim the bottom
    tot_height -= vert_spacing

    # Drop out early if there were no replays to process, tot_height of <0
    # throws errors
    if tot_height < 0:
        return None

    # Add them to the sheet image
    sheet = Image.new('RGBA', (max_width, tot_height), (255, 255, 255, 0))
    y_off = 0
    for line in lines:
        off_set = 0
        if line.size[0] < max_width:
            off_set = math.floor((max_width - line.size[0])/2)
        sheet.paste(line, (off_set, y_off), line)
        y_off += line.size[1]
        y_off += vert_spacing

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
