import json
import math
from datetime import datetime

from pathlib import Path
from typing import List

from herotools.HeroTools import (HeroIconPrefix, HeroIDType, convertName,
                                 hero_portrait, hero_portrait_prefix)
from herotools.lib.league import league_id_map
from herotools.important_times import tournament_list, ImportantTimes, nice_time_names
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from PIL import Image, ImageDraw

import StaticAnalysis
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.lib.metadata import has_networth
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.TeamSelections import TeamSelections
from StaticAnalysis.analysis.networth import get_laning_image
from StaticAnalysis import session, FONT_CACHE
import matplotlib.pyplot as plt

scims_json = StaticAnalysis.CONFIG['scrims']['SCRIMS_JSON']
try:
    with open(scims_json) as file:
        SCRIM_REPLAY_DICT = json.load(file)
except IOError:
    print(f"Failed to read scrim_list {scims_json}!")


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
    font = FONT_CACHE['arialbd.ttf', font_size]
    x_pos = math.floor(size[0]/2 - font.getlength(text)/2)
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
        font = FONT_CACHE['arialbd.ttf', font_size]
        # offset = font.getsize(text)[0]
        offset = font.getlength(text)
        text_canv.text(((size[1] - offset)/2, 0), text=text,
                       font=font, fill=(255, 255, 255))

        text_image = text_image.rotate(90, expand=1)
        px, py = 0, 0
        sx, sy = text_image.size
        out_box.paste(text_image, (px, py, px + sx, py + sy), text_image)

    return out_box


image_cache = {}
def hero_box_image_portrait(
    hero: str, is_pick: bool, pick_num: int, add_textbox: bool = True,
    add_order: bool = True):
    image: str = hero_portrait[hero]
    if not is_pick:
        image = image.replace(".png", "_grey.png")
    portrait_location = hero_portrait_prefix / image

    if portrait_location not in image_cache:
        image_cache[portrait_location] = Image.open(portrait_location).convert('RGBA')
    portrait = image_cache[portrait_location]

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
    if add_textbox:
        size = (text_box_x + 2*boarder,
                text_box_y + dimensions[1] + 2*boarder + y_spacing)
    else:
        size = (text_box_x + 2*boarder,
                dimensions[1] + 2*boarder + y_spacing)
    out_box = Image.new('RGBA', size, background_colour)
    canvas = ImageDraw.Draw(out_box)

    # Put in the portrait
    out_box.paste(portrait, (boarder, boarder), portrait)
    font = FONT_CACHE['arialbd.ttf', font_size]
    if add_textbox:
        if is_pick:
            text = "PICK"
            extra = hero_portrait_prefix.parent / "check_mark.png"
        else:
            text = "BAN"
            extra = hero_portrait_prefix.parent / "x_mark.png"

        if (extra, font_size) not in image_cache:
            image_cache[(extra, font_size)] = Image.open(extra).convert('RGBA').resize((font_size, font_size))
        extra_graphic = image_cache[(extra, font_size)]

        # extra_graphic = Image.open(extra).convert("RGBA")
        # extra_graphic = extra_graphic.resize((font_size, font_size))

        # Text box
        canvas.rectangle((boarder, text_off_y,
                        boarder + text_box_x,
                        text_off_y + text_box_y), fill='black')

        text_size = int(font.getlength(text))
        text_off = text_box_x // 2 - text_size // 2 + extra_graphic.size[0] // 2
        canvas.text((text_off, text_off_y + 1), text, fill='white',
                    font=font)

        # Add the extra graphic
        out_box.paste(extra_graphic, (text_off - font_size - 1, text_off_y + 2),
                    extra_graphic)

    # Number box, has to be drawn to temp canvas
    if add_order:
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
    # w, h = font.getsize(str(pick_num))
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
        font = FONT_CACHE['arialbd.ttf', font_size]
        outline_colour = (255, 255, 255, 255)
        left, top, right, bottom = font.getbbox(text)
        w, h = right - left, bottom - top
        x, y = (0, 0)
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
    add_order = True
    if team.firstPick is None:
        add_order = False
    height = 0
    for selection in team.draft:
        changed_phase = prev_is_pick != selection.is_pick
        prev_is_pick = selection.is_pick

        if selection.is_pick:
            extra_space_pick.append(changed_phase)
            hbox = hero_box_image_portrait(selection.hero,
                                           selection.is_pick,
                                           selection.order,
                                           add_textbox=False,
                                           add_order=add_order)
            tot_width_pick += hbox.size[0]
            hero_boxes_pick.append(hbox)
            height = max(height, hbox.size[1] + spacing*2)
        else:
            extra_space_ban.append(changed_phase)
            hbox = hero_box_image_portrait(selection.hero,
                                           selection.is_pick,
                                           selection.order,
                                           add_textbox=False,
                                           add_order=add_order)
            tot_width_ban += hbox.size[0]
            hero_boxes_ban.append(hbox)
            height = max(height, hbox.size[1] + spacing*2)

    tot_width_pick += spacing
    tot_width_ban += spacing
    width = max(tot_width_ban, tot_width_pick)

    #b_colour = (255, 255, 255, 0)
    b_colour = (255, 255, 255, 255)
    #out_box = Image.new('RGBA', (max([tot_width_pick, tot_width_ban]), 2*height), b_colour)
    out_box = Image.new('RGBA', (width, 2*height), b_colour)

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


def process_team_dotabuff(replay: Replay, team: TeamSelections, spacing=5):
    tot_width = spacing
    # All the heroes as per dotabuff formatting
    pick_ban_box = process_team_portrait_dotabuff(replay, team, spacing=0)
    tot_width += pick_ban_box.size[0]
    # First pick indicator, y scaling to pick_ban_box
    firstpick_box = draw_firstpick_box(team, size=(17, pick_ban_box.size[1]))
    tot_width += firstpick_box.size[0]
    tot_width += spacing
    height = pick_ban_box.size[1] + 2 * spacing

    team_win = team.team == replay.winner
    #b_colour = (255, 255, 0, 255) if team_win else (255, 255, 255, 0)
    b_colour = (238, 130, 238, 255) if team_win else (255, 255, 255, 0)

    out_box = Image.new('RGBA', (tot_width, height), b_colour)

    # Paste in first pick indicator
    out_box.paste(firstpick_box,
                  (spacing, spacing),
                  firstpick_box)
    # Paste in dotabuff formatted heroes
    out_box.paste(pick_ban_box,
                  (spacing+firstpick_box.size[0], spacing),
                  pick_ban_box)

    return out_box


def add_line_text(
    replay:Replay, main_team: TeamInfo, draft_image: Image,
    is_scrim: bool, add_league_date: bool, spacing: int) -> Image:

    # Get the name
    main_side = replay.get_side(main_team)
    if main_side is None:
        print(f"[Draft] Failed to find main team {main_team.name} in {replay.replayID}")
        return
    elif main_side == Team.DIRE:
        main_name = "Dire"
        opp_name = replay.get_nice_side_name(Team.RADIANT)
    elif main_side == Team.RADIANT:
        main_name = "Radiant"
        opp_name = replay.get_nice_side_name(Team.DIRE)
    # Get the winner
    if main_side == replay.winner:
        main_name += " (winner)"
    else:
        opp_name += " (winner)"
        
    font_size = 17
    first_pick_box_offset = 17
    font = FONT_CACHE['arialbd.ttf', font_size]
    text_canv = ImageDraw.Draw(draft_image)
    # Opposition name
    text_canv.text(
        xy=(draft_image.size[0]//2 + spacing + first_pick_box_offset, spacing),
        text=opp_name, font=font, fill='black')
    text_canv.text(
        xy=(450, spacing),
        text="Arr", font=font)
    # Main team name
    if main_side == Team.DIRE:
        text_canv.text(
            xy = (first_pick_box_offset + spacing, spacing), text=main_name,
            font=font, fill=(168, 56, 6))
    elif main_side == Team.RADIANT:
        text_canv.text(
            xy = (first_pick_box_offset + spacing, spacing), text=main_name,
            font=font, fill=(89, 131, 7)
            )
    if add_league_date:
        lfont_size = 12
        font = FONT_CACHE['arialbd.ttf', lfont_size]
        replay_time: datetime = replay.endTimeUTC
        ago = (ImportantTimes['Now'] - replay_time).days
        date_str = replay_time.strftime(r"%b %d %Y")
        replay_id = str(replay.replayID)
        text = f"{replay_id}, {date_str}, {ago} days ago"
        text_canv.text(
            xy=(draft_image.size[0] - spacing, spacing),
            text=text, anchor='ra', font=font, fill='black', stroke_width=0,
        )
    if is_scrim:
        # Add a circle
        x = (first_pick_box_offset + spacing)//2
        y = (font_size + spacing) // 2 + spacing
        rad = min(x, y)//2
        text_canv.circle((x,y), radius=rad, fill='yellow', width=1, outline='black')
    
    return draft_image


def pickban_line_image(replay: Replay, team: TeamInfo, spacing=5,
                       add_team_name=True, add_league_date=True, caching=True,
                       add_lane_outcome=False, is_scrim=False,
                       fig=plt.gcf()):
    has_nw = has_networth(session, replay)
    if caching:
        cache_dir = Path(StaticAnalysis.CONFIG['cache']["CACHE"])
        if not has_nw or not add_lane_outcome:
            file_name = f"{replay.replayID}_{team.name}_draftonly.png"
        else:
            file_name = f"{replay.replayID}_{team.name}.png"
        file_path = cache_dir / file_name
        if file_path.exists():
            if file_path not in image_cache:
                image_cache[file_path] = Image.open(file_path)
            pb_line = image_cache[file_path]
            pb_line = add_line_text(replay, team, pb_line, is_scrim, add_league_date, spacing)
            return pb_line

    t: TeamSelections
    for t in replay.teams:
        team_win = t.team == replay.winner
        if len(t.draft) == 0:
            print("Failed to get draft for {} in replay {}".format(str(t.team), t.replay_ID))
            return None
        if t.teamID == team.team_id or t.stackID == team.stack_id or t.stackID == team.extra_stackid:
            team_line = process_team_dotabuff(replay, t)
            main_team_faction = t.team

            if main_team_faction == Team.DIRE:
                main_name = "Dire"
            else:
                main_name = "Radiant"
            if team_win:
                main_name += " (winner)"
        else:
            opposition_line = process_team_dotabuff(replay, t)
            opp_name = SCRIM_REPLAY_DICT.get(str(replay.replayID), t.teamName)
            try:
                opp_name = SCRIM_REPLAY_DICT[str(team.team_id)][str(replay.replayID)]
            except KeyError:
                opp_name = t.teamName
            if opp_name is None:
                opp_name = "Dire" if t.team == Team.DIRE else "Radiant"
            if team_win:
                opp_name += " (winner)"


    # Team spacer
    spacer = Image.new('RGB', (10, team_line.size[1]), (255,255,255,0))
    spacerDraw = ImageDraw.Draw(spacer)
    spacerDraw.line([(0,0),(0,team_line.size[1])], fill='black', width=2*spacing)

    # Lane outcome line
    # Add networth line
    if has_nw and add_lane_outcome:
        lane_outcome = get_laning_image(session, fig, main_team_faction, replay)
    else:
        lane_outcome = None
    fig.clf()

    font_size = 17
    text_height = font_size + 2*spacing
    height = team_line.size[1] + text_height
    width = (draft_width := team_line.size[0] + spacer.size[0] + opposition_line.size[0])
    if lane_outcome is not None:
        width = max(width, lane_outcome.size[0])
        y_lanepos = height
        height += lane_outcome.size[1]
        x_lanepos = (width - lane_outcome.size[0]) // 2

    # Probably zero but there might be edge cases where lane outcome is larger
    x_draft_off = (width - draft_width) // 2

    out_box = Image.new('RGB', (width, height), (255, 255, 255, 0))

    out_box.paste(team_line, (x_draft_off, text_height), team_line)
    out_box.paste(
        opposition_line, (team_line.size[0] + spacer.size[0] + x_draft_off, text_height)
        )

    if lane_outcome is not None:
        out_box.paste(lane_outcome, (x_lanepos, y_lanepos), lane_outcome)

    if caching:
        cache_dir = Path(StaticAnalysis.CONFIG['cache']["CACHE"])
        if lane_outcome is None:
            file_name = f"{replay.replayID}_{team.name}_draftonly.png"
        else:
            file_name = f"{replay.replayID}_{team.name}.png"
        file_path = cache_dir / file_name
        assert file_path.exists() is False
        out_box.save(file_path)

    out_box = add_line_text(replay, team, out_box, is_scrim, add_league_date, spacing)

    return out_box


def relevant_tournament_times(replay: Replay, tournaments: List[str] = tournament_list):
    '''
    Get a list of tournaments from tournaments that occur after the replay, ordered by time.
    '''
    tournaments = sorted(tournaments, key=lambda x: ImportantTimes[x])
    output = []
    for tournament in tournaments:
        if ImportantTimes[tournament] > replay.endTimeUTC:
            output.append(tournament)

    return output


# https://stackoverflow.com/questions/312443/how-do-i-split-a-list-into-equally-sized-chunks
def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def draw_tournament_linebreak(text: str, width: int, height: int = 30, font_size: int = 17):
    side_spacing = 2
    # Canvas for drawing
    spacer = Image.new('RGB', (width, height), (255,255,255,0))
    spacerDraw = ImageDraw.Draw(spacer)

    # Text
    font = FONT_CACHE['arialbd.ttf', font_size]
    text_w = spacerDraw.textlength(text, font=font)
    text_start = (width - text_w)//2
    text_end = text_start + text_w
    spacerDraw.text(
        xy=(text_start, (height - font_size)//2),
        text=text,
        font=font,
        fill='black'
        )
    #[(x0, y0), (x1, y1)] or [x0, y0, x1, y1]
    top_line_height = height//2 + side_spacing
    bottom_line_height = height//2 - side_spacing
    spacerDraw.line(
        [(side_spacing, top_line_height), (text_start - 2*side_spacing, top_line_height)],
        fill='black',
        width=2
        )
    spacerDraw.line(
        [(side_spacing, bottom_line_height), (text_start - 2*side_spacing, bottom_line_height)],
        fill='black',
        width=2
        )
    spacerDraw.line(
        [(text_end + 2*side_spacing, top_line_height), (width - side_spacing, top_line_height)],
        fill='black',
        width=2
        )
    spacerDraw.line(
        [(text_end + 2*side_spacing, bottom_line_height), (width - side_spacing, bottom_line_height)],
        fill='black',
        width=2
        )
    
    return spacer

def replay_draft_image(
    replays: List[Replay], team: TeamInfo, team_name: str,
    first_pick=True, second_pick=True, line_limit=9,
    scrim_list: list=None):
    line_sets = list()
    line_lengths = list()
    max_width = 0
    vert_spacing = 3

    # fig for networths
    fig = plt.gcf()

    # Tournaments that need to be considered for breaks
    # Assumes last replay is the oldest!
    try:
        tournaments = relevant_tournament_times(replays[-1])
    except IndexError:
        tournaments = []
    # Get the lines for each replay and store so we can build our sheet
    lines = []
    tot_height = 0
    replay: Replay
    for replay in replays:
        # Check to see if our team is picked first
        # If it is our team then this is true if they had first pick too, else false
        if (replay.teams[0].teamID == team.team_id or
            replay.teams[0].stackID == team.stack_id or
            replay.teams[0].stackID == team.extra_stackid):
            team_num = 0
        else:
            team_num = 1
        is_first = replay.teams[team_num].firstPick

        if is_first and not first_pick:
            continue
        if not is_first and not second_pick:
            continue

        if scrim_list and str(replay.replayID) in scrim_list:
            is_scrim = True
        else:
            is_scrim = False

        line = pickban_line_image(replay, team, add_team_name=True,
                                  caching=True, fig=fig, is_scrim=is_scrim)
        if line is None:
            continue
        max_width = max(max_width, line.size[0])
        # Check our time now so we have a width reference to work with!
        try:
            t_time = ImportantTimes[tournaments[-1]]
            if replay.endTimeUTC < t_time:
                # Replay was after the tournament start
                t_name = tournaments.pop()
                try:
                    t_text = nice_time_names[t_name]
                except KeyError:
                    t_text = t_name
                    print(f"No nice name for tournament {t_name}.")
                t_break = draw_tournament_linebreak(text=t_text, width=max_width)
                lines.append(t_break)
                tot_height += t_break.size[1]
        except IndexError:
            pass
        lines.append(line)
        tot_height += line.size[1]
        tot_height += vert_spacing
        # if len(lines) >= line_limit:
        # Estimated
        if tot_height >= 1700:
            line_sets.append(lines)
            lines = []

            # Remove one to trim the bottom
            tot_height -= vert_spacing
            line_lengths.append(tot_height)
            tot_height = 0
    # Last batch
    line_sets.append(lines)
    tot_height -= vert_spacing
    line_lengths.append(tot_height)

    # Drop out early if there were no replays to process, tot_height of <0
    # throws errors
    if not line_sets:
        return []
    if not line_sets[0]:
        return []

    # Add them to the sheet image
    sheets = []
    font_size = 20
    first_sheet = True  # Then we add names
    for lines, tot_height in zip(line_sets, line_lengths):
        if tot_height <= 0:
            continue
        if first_sheet:
            sheet = Image.new('RGB', (max_width, tot_height + font_size + 5),
                              (255, 255, 255, 255))
            canvas = ImageDraw.Draw(sheet)

            font = FONT_CACHE['arialbd.ttf', font_size]
            canvas.text((5, 0), team_name, fill='black', font=font)
            canvas.text((sheet.size[0]/2 + 5, 0), 'Opponent', fill='black',
                        font=font)
            y_off = font_size + 5
            first_sheet = False
        else:
            sheet = Image.new('RGB', (max_width, tot_height),
                              (255, 255, 255, 255))
            y_off = 0
        for line in lines:
            off_set = 0
            if line.size[0] < max_width:
                off_set = math.floor((max_width - line.size[0]) / 2)
            sheet.paste(line, (off_set, y_off))
            y_off += line.size[1]
            y_off += vert_spacing
        sheets.append(sheet)

    return sheets
