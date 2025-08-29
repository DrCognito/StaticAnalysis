from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from StaticAnalysis.replays.Ward import Ward
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.lib.Common import EXTENT, add_map
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.Common import Team, WardType
from pandas import DataFrame, read_sql, Series
from herotools.important_times import MAIN_TIME
from sqlalchemy import or_, and_
from StaticAnalysis.analysis.ward_vis import plot_image_scatter
from PIL.Image import open as Image_open
import StaticAnalysis
import matplotlib.pyplot as plt
from typing import Iterable
from StaticAnalysis.analysis.draft_vis import hero_box_image_portrait
from StaticAnalysis.analysis.route_vis import plot_pregame_players
from PIL import Image, ImageDraw

falcons = get_team(9247354)
spirit = get_team(7119388)
r_filter = Replay.endTimeUTC >= MAIN_TIME
replays = spirit.get_replays(session).filter(r_filter)

test_replay: Replay = replays[0]
side = test_replay.get_side(spirit)
players = list(test_replay.get_players(side))
players[0].get_networth_at(0)
endr = test_replay.gameEnd

def decorate_networth_rank(players:Iterable[Player]):
    decorated = [
        (-1*p.get_final_networth(), p) for p in players
    ]

    return decorated



def decorate_player_position(players: Iterable[Player], team: TeamInfo):
    # Map steam id to pos
    positions = {v.player_id:k for k,v in enumerate(team.players)}
    decorated = [
        (positions.get(p.steamID, 999), p) for p in players
    ]
    
    return decorated


def decorate_pos_estimate(replay: Replay, side: Team, team: TeamInfo | None):
    # Get the pos ranked player list
    players = set(replay.get_players(side))
    
    positions = [0,1,2,3,4]
    output = []
    if team is not None:
        pos_rank = decorate_player_position(players, team)
        for i, (pos, player) in enumerate(pos_rank):
            if pos in positions:
                # Add decorated to the output
                output.append((pos, player))
                # Remove found players
                players.remove(player)
                positions.remove(pos)

    # Rank remaining by networth
    nw_rank = sorted(decorate_networth_rank(players))
    for pos, (_, p) in zip(positions, nw_rank):
        output.append((pos, p))
        
    return output

test = decorate_pos_estimate(test_replay, side, spirit)
heroes = [p.hero for _, p in sorted(test)]

def process_team_picks(heroes: list[str], spacing=5):
    portraits = [
        hero_box_image_portrait(
            hero=h, is_pick=True, pick_num=99, add_order=False, add_textbox=False) for h in heroes
    ]

    tot_width = spacing
    # Add the portrait widths
    tot_width += sum(x + spacing for x,_ in map(lambda x: x.size, portraits))
    # Get the max height
    height = max(y + 2*spacing for _,y in map(lambda x: x.size, portraits))
    b_colour = (255, 255, 255, 0)
    out_box = Image.new('RGBA', (tot_width, height), b_colour)

    processed_size = spacing
    extras = 0
    for i, hbox in enumerate(portraits):
        # Initial offset starts after the border (+spacing)

        x_off = processed_size + extras
        out_box.paste(hbox,
                      (x_off, spacing),
                      hbox)
        processed_size += hbox.size[0]

    return out_box

test_line = process_team_picks(heroes)

fig = plt.figure(figsize=(7, 7))
plot_pregame_players(test_replay, spirit, side, session, team_session, fig)
fig.tight_layout()