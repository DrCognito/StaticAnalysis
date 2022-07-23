import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.minimal_db as db
from replays.Replay import Replay
from lib.important_times import ImportantTimes
from analysis.Player import player_heroes
from analysis.visualisation import make_image_annotation
import matplotlib.pyplot as plt
from pandas import DataFrame
from matplotlib.figure import Figure
from lib.HeroTools import HeroIconPrefix, HeroIDType, convertName, heroShortName

team = db.get_team(2586976)
# team = db.get_team(15)
# team = db.get_team(7554697)

r_filter = Replay.endTimeUTC >= ImportantTimes['DPC2022_T3']
hero_picks_df = player_heroes(db.session, team, r_filt=r_filter, summarise=200)

def is_flex(*args):
    pass_count = 0
    for p in args:
        if p >= 1:
            pass_count += 1
    
    #return pass_count > 1
    return pass_count

# pass_filter = hero_picks_df.apply(lambda x: is_flex(*x), axis=1)
hero_picks_df['Counts'] = hero_picks_df.apply(lambda x: is_flex(*x), axis=1)
flex_df = hero_picks_df.query('Counts > 1')
flex_df['std'] = flex_df.iloc[:, 0:-1].std(axis=1)
flex_df = flex_df.sort_values(['Counts', 'std'], ascending=True)


def plot_flex_picks(data: DataFrame, fig: Figure):
    print(data)
    player_bars_x = {p: list() for p in data.columns}
    player_bars_y = {p: list() for p in data.columns}
    x_ticks = []
    x_labels = []

    hero_icons = {}
    b_width = 0.5
    set_gap = 2*b_width
    position = 0.0

    # iterrows tuple, [0] is index, [1] series for row
    for row in data.iterrows():
        entries = 0
        hero_icons[row[0]] = position
        for player, count in row[1].iteritems():
            if count == 0:
                continue
            player_bars_x[player].append(position)
            player_bars_y[player].append(count)

            x_ticks.append(position)
            x_labels.append(player)

            position += b_width
            entries += 1
        # In a long set add a little padding to the icon
        # if entries > 2:
        #     hero_icons[row[0]] += b_width
        # Add gap between heroes
        position += set_gap

    position -= set_gap

    fig.set_dpi(50)
    print(f"Pos: {position}, 20/position {20/position}")
    fig.set_size_inches(6, 0.36*position)
    axe = fig.subplots()

    for player in player_bars_x:
        axe.barh(player_bars_x[player], player_bars_y[player],
                height=0.7*b_width, label=player)
        axe.set_yticks(x_ticks, x_labels, rotation=45, fontsize=7)
    # axe.yaxis.labelpad = 20
    # axe.xticks(rotation=45)
    # Add heroes
    y_min, y_max = axe.get_ylim()
    y_range = y_max - y_min
    size = 0.8
    x_pos = -0.2
    for hero in hero_icons:
        try:
            # Get and resize the hero icon.
            icon = HeroIconPrefix / convertName(hero, HeroIDType.NPC_NAME,
                                                HeroIDType.ICON_FILENAME)
        except (ValueError, KeyError):
            print("Unable to find hero icon for: " + hero)
            continue
        y_rel = (float(hero_icons[hero]) - y_min)/y_range
        artist = make_image_annotation(icon, axe, x_pos, y_rel, size)
        # extra_artists.append(artist)
    # axe.invert_yaxis() 
    axe.legend()
    plt.subplots_adjust(left=0.2)

    return fig, axe


fig = plt.figure()
f, a = plot_flex_picks(flex_df.iloc[:, 0:-2], fig)
plt.show()
fig.savefig("test.png")
# sns.catplot(x = "x",       # x variable name
#             y = "y",       # y variable name
#             hue = "type",  # group variable name
#             data = flex_df,     # dataframe to plot
#             kind = "bar")

# test = flex_df.reset_index().melt(id_vars='index')
# sns.catplot(x='value', y='index', hue='variable', data = test, kind='bar', orient='h')

#hero_picks_df.iloc[:, 0:-1]