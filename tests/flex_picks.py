import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.minimal_db as db
from replays.Replay import Replay
from lib.important_times import ImportantTimes
from analysis.Player import player_heroes
import matplotlib.pyplot as plt
import seaborn as sns

team = db.get_team(2586976)

r_filter = Replay.endTimeUTC >= ImportantTimes['DPC2022_T3']
hero_picks_df = player_heroes(db.session, team, r_filt=r_filter, summarise=200)

def is_flex(*args):
    pass_count = 0
    for p in args:
        if p >= 1:
            pass_count += 1
    
    #return pass_count > 1
    return pass_count

pass_filter = hero_picks_df.apply(lambda x: is_flex(*x), axis=1)
flex_df = hero_picks_df[pass_filter > 1]

# sns.catplot(x = "x",       # x variable name
#             y = "y",       # y variable name
#             hue = "type",  # group variable name
#             data = flex_df,     # dataframe to plot
#             kind = "bar")

test = flex_df.reset_index().melt(id_vars='index')
sns.catplot(x='value', y='index', hue='variable', data = test, kind='bar', orient='h')

#hero_picks_df.iloc[:, 0:-1]