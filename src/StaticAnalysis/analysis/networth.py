from enum import Enum

import matplotlib.pyplot as plt
from herotools.HeroTools import (HeroIconPrefix, HeroIDType, convertName,
                                 heroShortName)
from matplotlib.axes import Axes
from matplotlib.cm import get_cmap
from pandas import DataFrame, read_sql
from PIL import Image

from StaticAnalysis.analysis.Player import (closest_tower,
                                            player_positioning_replay)
from StaticAnalysis.analysis.visualisation import make_image_annotation
from StaticAnalysis.lib.Common import dire_towers, fig2img, radiant_towers
from StaticAnalysis.replays.Player import NetWorth, Player, PlayerStatus
from StaticAnalysis.replays.Replay import Replay, Team


scheme_geo = ['top', 'mid', 'bottom']
scheme_log = ['safe', 'mid', 'off']


def get_laning_image(session, fig, main_team: Team,
                     replay: Replay = None, replay_id: int = None,
                     time_limit: int = 60 * 7, scheme=scheme_geo) -> Image:

    lane_res = get_lane_results(session,
                                replay=replay, replay_id=replay_id,
                                time_limit=time_limit, scheme=scheme)

    if lane_res.empty:
        return None

    fig = plot_networth_bar(fig, lane_res, main_team, scheme)
    fig.subplots_adjust(wspace=0.05, left=0.02, right=0.98, top=0.99, bottom=0.1)

    return fig2img(fig)


def get_lane_results(session, replay: Replay = None, replay_id: int = None,
                     time_limit: int = 7 * 60, scheme=scheme_log):
    if replay is None and replay_id is None:
        print("Must pass either a replay or replay_id!")
        raise ValueError
    if replay is not None:
        replay_id = replay.replayID
    query = (
        session.query(NetWorth.replayID, NetWorth.hero, NetWorth.team, NetWorth.networth)
               .filter(NetWorth.replayID == replay_id, NetWorth.game_time == time_limit)
    )

    # Initial Networth full table for out time range
    df = read_sql(query.statement, session.bind).sort_values(by=['networth'], ascending=False)

    # We asign lanes by player positioning
    player_pos = player_positioning_replay(session, replay_id, start=0, end=time_limit, alive_only=True)
    player_pos = player_pos.with_entities(PlayerStatus.hero,
                                          PlayerStatus.xCoordinate,
                                          PlayerStatus.yCoordinate,
                                          PlayerStatus.team)

    pos_df = read_sql(player_pos.statement, session.bind)

    # Asign a lane for each time position
    def _asign_lane(row):
        x = row['xCoordinate']
        y = row['yCoordinate']
        if row['team'] == Team.DIRE:
            tower_dict = dire_towers
        if row['team'] == Team.RADIANT:
            tower_dict = radiant_towers

        return closest_tower((x, y), tower_dict, scheme=scheme)
    pos_df['lane'] = pos_df.apply(_asign_lane, axis=1)
    # Summarise by grouping up and using the top value count
    lanes = pos_df.groupby(by=['team', 'hero',])['lane'].apply(lambda x: x.value_counts().index[0])
    # Add the lane info and group up
    df['lane'] = df.apply(lambda x: lanes[x['team'], x['hero']], axis=1)
    lane_diff = df.groupby(['team', 'lane']).agg({'hero': list, 'networth': sum})

    return lane_diff


def add_icons(axis: Axes, hero_list: list, left=True):
    def _icon_conv(h):
        return HeroIconPrefix / convertName(h, HeroIDType.NPC_NAME, HeroIDType.ICON_FILENAME)
    icons = [_icon_conv(h) for h in hero_list]
    icon_size = 0.7
    if left:
        spacing = [0.5 / x for x in range(1, 6)]
        spacing = [0, 0.11, 0.22, 0.33, 0.44]
    else:
        spacing = [1.0 - 0.5 / x for x in range(1, 6)]
        spacing = [1.0, 0.89, 0.78, 0.67, 0.56]

    extra_ents = []
    for icon, x_pos in zip(icons, spacing[::-1]):
        ent = make_image_annotation(icon, axis, x_pos, 0.68, size=icon_size)
        extra_ents.append(ent)

    return extra_ents


def plot_networth(axis: Axes, main_team, opposition, plot_fraction=True):
    heroes_left = main_team['hero']
    heroes_right = opposition['hero']
    result = main_team['networth'] - opposition['networth']

    significance_percent = 0.1
    pos_map = get_cmap("Greens")
    neg_map = get_cmap("Reds")
    if result < 0:
        fraction = main_team['networth'] / opposition['networth']
        if fraction < (1.0 - significance_percent):
            outcome = "L"
        else:
            outcome = "D"
        col = neg_map(fraction)
        out_col = 'red'
        text = f" {result}gp ({outcome})"
        textx = -1.0
        ha = "left"
        frac_diff = fraction - 1
    else:
        fraction = opposition['networth'] / main_team['networth']
        if fraction < (1.0 - significance_percent):
            outcome = "W"
        else:
            outcome = "D"
        col = pos_map(fraction)
        out_col = 'green'
        text = f"{result}gp ({outcome}) "
        textx = 1.0
        ha = "right"
        frac_diff = 1 - fraction

    tcol = 'black'
    y = [0,]
    barheight = 0.4
    if plot_fraction:
        axis.barh(y, [frac_diff,], height=barheight, color=col, edgecolor=out_col)
        axis.set_xlim(-1.0, 1.0)
    else:
        axis.barh(y, [result,], height=barheight, color=col, edgecolor=out_col)
        axis.set_xlim(-2500, 2500)
    axis.set_ylim(0, 0.5)
    # Add line at 0
    axis.axvline(0, 0, 1.0, color='black')
    # Clean up axis
    axis.yaxis.set_ticks([])
    axis.axes.xaxis.set_ticklabels([])
    axis.spines['top'].set_visible(False)
    axis.spines['right'].set_visible(False)
    axis.spines['left'].set_visible(False)

    # Text
    # axis.text(x=textx, y=barheight/2, s=text,
    #           ha=ha, va="bottom",
    #           color=tcol, fontsize=12)
    axis.text(x=textx, y=0, s=text,
              ha=ha, va="bottom",
              color=tcol, fontsize=12)
    
    # Hero icons
    add_icons(axis, heroes_left, left=True)
    add_icons(axis, heroes_right, left=False)

    return axis


def plot_networth_bar(fig, networths: DataFrame, main_team: Team, scheme):
    # Main team should be on the left always
    order = scheme

    # For dire top is safe, bottom is off
    if main_team == Team.DIRE:
        opp_team = Team.RADIANT
        order = scheme_geo
    if main_team == Team.RADIANT: # Reversed for Radiant, reverse the scheme!
        opp_team = Team.DIRE
        order = scheme_geo[::-1]

    axes = fig.subplots(1, 4)
    fig.set_figheight(0.6)
    fig.set_figwidth(11.69)
    for o, axis in zip(order, axes[:3]):
        main = networths.loc[main_team, o]
        opp = networths.loc[opp_team, o]
        plot_networth(axis, main, opp)


    # Also do a summary!
    main = networths.loc[main_team].sum()
    opp = networths.loc[opp_team].sum()
    plot_networth(axes[-1], main, opp)

    return fig