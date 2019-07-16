import Setup
import os
import sys
from os import environ as environment
from typing import List
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Ward import Ward, WardType
from replays.Replay import Replay
from replays.Player import Player
from replays.Smoke import Smoke
from lib.team_info import InitTeamDB, TeamInfo, TeamPlayer
from analysis.Replay import get_ptbase_tslice
from pandas import DataFrame, read_sql
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.image as mpimg
from dotenv import load_dotenv

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()
load_dotenv(dotenv_path="../setup.env")


def get_team(name):
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == name).one_or_none()

    return team


def get_player(steam_id: int):
    player = team_session.query(TeamPlayer.name)\
                         .filter(TeamPlayer.player_id == steam_id)\
                         .one_or_none()
    print(steam_id, player)
    if player is None:
        print("Steam id {} not found.".format(steam_id))
        raise ValueError
    else:
        return player[0]


def get_player_map(steam_ids: set)-> dict():
    unknown_count = 0
    output = {}
    for i in steam_ids:
        try:
            output[i] = get_player(int(i))
        except ValueError:
            output[i] = "Un" + str(unknown_count)
            unknown_count += 1

    return output


def get_player_init(names: List[str])-> List[str]:
    # Try first two
    initials = {x:x[:2] for x in names}
    unique = set(list(initials.values()))
    if len(unique) == len(names):
        return initials

    # Ok got dups, correct them using numbers instead
    fixed = {}
    totals = {}
    unique = set()
    for i, s in initials.iteritems():
        if s in totals:
            new_i = s
            while new_i in totals:
                totals[s] += 1
                new_i = s[0] + str(totals[s])
            fixed[i] = new_i
        else:
            totals[s] = 0
            fixed[i] = s

    return fixed


# Dire 4901517396
# Radiant 4901403209
team = get_team("Royal Never Give Up")
r_query = team.get_replays(session).filter(Replay.replayID == 4857623860)
#d_query = team.get_replays(session).filter(Replay.replayID == 4901517396)
_, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                              Type=Ward,
                                              start=-2*60, end=20*60)
# wards_dire, _ = get_ptbase_tslice(session, d_query, team=team,
#                                               Type=Ward,
#                                               start=-2*60, end=20*60)
# wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
print(wards_radiant.count())
wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)
print(wards_radiant.count())


sql_query = wards_radiant.with_entities(Ward.xCoordinate,
                Ward.yCoordinate,
                Ward.steamID,
                Ward.game_time,
                Ward.from_smoke).statement

data = read_sql(sql_query, session.bind)
smoked_wards = data.loc[data["anon_1"] == True]
name_map = get_player_map(set(data['steamID'].unique()))
initial_map = get_player_init(name_map.values())

data['Name'] = data['steamID'].map(name_map)
data['Initials'] = data['Name'].map(initial_map)

smokes = session.query(Smoke).filter(Smoke.replayID == 4903243468)
tp = smokes[1].players_smoked
sigh = [x.steam_id for x in tp]

fig, ax = plt.subplots(figsize=(10, 13))


def plot_overlayed_smokes(data: DataFrame, ax_in):
    # Pre game to 20mins
    vmin = -120
    vmax = 20*60
    jet = plt.get_cmap('afmhot')

    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')
    ax_in.set_xlim(0, 1)
    ax_in.set_ylim(0, 1)

    smoke_data = data.loc[data["anon_1"] == True]
    normal_data = data.loc[data["anon_1"] == False]

    # ax_in.scatter(x=smoke_data['xCoordinate'],
    #               y=smoke_data['yCoordinate'],
    #               y=smoke_data['game_time'],
    #               edgecolor='gray', linewidth='3',
    #               vmin=vmin, vmax=vmax)

    ax_in.scatter(x=smoke_data['xCoordinate'],
                  y=smoke_data['yCoordinate'],
                  c=smoke_data['game_time'],
                  edgecolor='grey', linewidth=3,
                  marker='1',
                  s=250, cmap='gist_rainbow',
                  alpha=0.75,
                  vmin=vmin, vmax=vmax,
                  zorder=3)

    ax_in.scatter(x=normal_data['xCoordinate'],
                  y=normal_data['yCoordinate'],
                  c=normal_data['game_time'],
                  edgecolor='g', linewidth=3,
                  s=250, cmap='gist_rainbow',
                  alpha=0.75, marker='2',
                  vmin=vmin, vmax=vmax,
                  zorder=2)

    table_test = data[['Initials', 'game_time']][0:3]
    ax_in.table(cellText=table_test.values,
                rowLabels=table_test.index,
                colLabels=table_test.columns,
                bbox=[0, 0, 0.2, 0.05], zorder=2)
    ax_in.table(cellText=table_test.values,
                rowLabels=table_test.index,
                colLabels=table_test.columns,
                loc='top')
plot_overlayed_smokes(data, ax)
plt.show()