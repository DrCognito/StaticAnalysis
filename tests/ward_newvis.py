import Setup
import os
import sys
from os import environ as environment
from typing import List
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Ward import Ward, WardType
from replays.Replay import Replay, Team
from replays.Player import Player
from replays.Smoke import Smoke
from replays.TeamSelections import TeamSelections
from lib.team_info import InitTeamDB, TeamInfo, TeamPlayer
from analysis.Replay import get_ptbase_tslice
from pandas import DataFrame, read_sql
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.image as mpimg
from dotenv import load_dotenv
from datetime import timedelta
from math import sin, cos, radians
import matplotlib.patheffects as PathEffects
from sklearn.cluster import KMeans
from adjustText import adjust_text
from analysis.draft_vis import hero_box_image, process_team
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()
load_dotenv(dotenv_path="../setup.env")


def nice_time(s):
    if s < 0:
        mins, sec = divmod(-1*s, 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "-{}:{}".format(mins, sec)
    else:
        mins, sec = divmod(s, 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "{}:{}".format(mins, sec)

    return time


def get_team(name):
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == name).one_or_none()

    return team


def get_player(steam_id: int):
    player = team_session.query(TeamPlayer.name)\
                         .filter(TeamPlayer.player_id == steam_id)\
                         .first()
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
team = get_team("Chaos Esports")
r_query = team.get_replays(session).filter(Replay.replayID == 4903243468)
d_query = team.get_replays(session).filter(Replay.replayID == 4903243468)
_, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                              Type=Ward,
                                              start=-2*60, end=20*60)
wards_dire, _ = get_ptbase_tslice(session, d_query, team=team,
                                              Type=Ward,
                                              start=-2*60, end=20*60)
wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
print(wards_radiant.count())
wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)
print(wards_radiant.count())


sql_query = wards_radiant.with_entities(Ward.xCoordinate,
                Ward.yCoordinate,
                Ward.steamID,
                Ward.game_time,
                Ward.from_smoke,
                Ward.replayID,
                Ward.ward_type).statement

data = read_sql(sql_query, session.bind)
smoked_wards = data.loc[data["anon_1"] == True]
name_map = get_player_map(set(data['steamID'].unique()))
initial_map = get_player_init(name_map.values())

data['Name'] = data['steamID'].map(name_map)
data['Initials'] = data['Name'].map(initial_map)
data['time'] = data['game_time'].map(nice_time)

# smokes = session.query(Smoke).filter(Smoke.replayID == 4903243468)
# tp = smokes[1].players_smoked
# sigh = [x.steam_id for x in tp]

fig, ax = plt.subplots(figsize=(10, 13))


def annotate_point(row, ax_in, disty=0.1, distx=0):
    if row['game_time'] < 0:
        mins, sec = divmod(-1*row['game_time'], 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "-{}:{}".format(mins, sec)
    else:
        mins, sec = divmod(row['game_time'], 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "{}:{}".format(mins, sec)
    if row['anon_1']:
        text = "(s){} {}".format(row['Initials'], time)
    else:
        text = "{} {}".format(row['Initials'], time)
    txt = ax_in.annotate(xy=(row['xCoordinate'], row['yCoordinate']),
                   xytext=(distx, disty),
                   textcoords='offset points',
                   s=text,
                   color='blue',
                   arrowprops=dict(arrowstyle='simple'),
                   path_effects=[PathEffects.withStroke(linewidth=3,
                   foreground="w")])

    return txt


def text_point(row, ax_in):
    if row['game_time'] < 0:
        mins, sec = divmod(-1*row['game_time'], 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "-{}:{}".format(mins, sec)
    else:
        mins, sec = divmod(row['game_time'], 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "{}:{}".format(mins, sec)
    if row['anon_1']:
        text = "(s){} {}".format(row['Name'], time)
    else:
        text = "{} {}".format(row['Name'], time)
    txt = ax_in.text(x=row['xCoordinate'], y=row['yCoordinate'],
                   s=text,
                   color='blue',
                   va='bottom',
                    ha='left',
                   path_effects=[PathEffects.withStroke(linewidth=3,
                   foreground="w")])

    return txt


def pos_vector(l: float, angle: float)->(float, float):
    rad = radians(angle)
    l2 = l + l*sin(angle/2)
    x = l * sin(rad)
    y = l * cos(rad)

    return x, y


def get_clusters(data: DataFrame, clusters=4) -> List[int]:
    kmeans = KMeans(n_clusters=clusters)
    kmeans.fit(data[['xCoordinate', 'yCoordinate']].values)
    print(kmeans.cluster_centers_)
    return kmeans.labels_


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
    # data['1dproj'] = data[['xCoordinate', 'yCoordinate']].apply(lambda x: (x[0])**2 + (1-x[1])**2, axis=1)
    data = data.sort_values(by='yCoordinate', ascending=False)

    # ax_in.scatter(x=smoke_data['xCoordinate'],
    #               y=smoke_data['yCoordinate'],
    #               y=smoke_data['game_time'],
    #               edgecolor='gray', linewidth='3',
    #               vmin=vmin, vmax=vmax)

    # ax_in.scatter(x=smoke_data['xCoordinate'],
    #               y=smoke_data['yCoordinate'],
    #               c=smoke_data['game_time'],
    #               edgecolor='grey', linewidth=3,
    #               marker='1',
    #               s=250, cmap='gist_rainbow',
    #               alpha=0.75,
    #               vmin=vmin, vmax=vmax,
    #               zorder=3)

    # ax_in.scatter(x=normal_data['xCoordinate'],
    #               y=normal_data['yCoordinate'],
    #               c=normal_data['game_time'],
    #               edgecolor='g', linewidth=3,
    #               s=250, cmap='gist_rainbow',
    #               alpha=0.75, marker='2',
    #               vmin=vmin, vmax=vmax,
    #               zorder=2)

    # table_test = data[['Initials', 'game_time']][0:3]
    # ax_in.table(cellText=table_test.values,
    #             rowLabels=table_test.index,
    #             colLabels=table_test.columns,
    #             bbox=[0, 0, 0.2, 0.05], zorder=2)
    # ax_in.table(cellText=table_test.values,
    #             rowLabels=table_test.index,
    #             colLabels=table_test.columns,
    #             loc='top')

    data['clusters'] = get_clusters(data)
    cluster_info = data.groupby(['clusters',])['xCoordinate'].nunique()
    cluster_tots = cluster_info.to_dict()
    deg_per_row = 360 / data.shape[0]
    # for j, row in data.iterrows():
    #     # deg_per_row = 360 / cluster_info.iloc[row['clusters']]
    #     i = cluster_tots[row['clusters']]
    #     cluster_tots[row['clusters']] += -1
    #     x, y = pos_vector(40, deg_per_row*j)
    #     annotate_point(row, ax_in, distx=x, disty=y)

    texts = []
    for j, row in data.iterrows():
        texts.append(text_point(row, ax_in))

    # adjust_text(texts, ax=ax_in,
    #             x=data['xCoordinate'], y=data['yCoordinate'],
    #             force_points=(0.05,0.05),
    #             expand_text=(1.1, 2),
    #             only_move={'points':'xy', 'text':'xy'},
    #             va='bottom',
    #             ha='left',
    #             arrowprops=dict(arrowstyle='->', color='r'),)
    adjust_text(texts, ax=ax_in,
                va='bottom',
                ha='left',
                arrowprops=dict(arrowstyle='->', color='r', lw=2),)


plot_overlayed_smokes(data, ax)
#plt.show()
replay: Replay = r_query.first()
t: TeamSelections
for t in replay.teams:
    if t.team == Team.RADIANT:
        rdraft = process_team(replay, t)
        rname = t.teamName
    else:
        ddraft = process_team(replay, t)
        dname = t.teamName


def add_draft(draft, pos, ax_in, size=1.0):
    # Resize if necessary
    if size != 1.0:
        width, height = draft.size
        width = width*size
        height = height*size
        draft.thumbnail((width, height))

    imagebox = OffsetImage(draft)
    imagebox.image.axes = ax_in

    ab = AnnotationBbox(imagebox, pos,
                        xycoords='data',
                        boxcoords="offset points",
                        pad=0,
                        frameon=False
                        )

    ax_in.add_artist(ab)

    return ab


def add_draft2(draft, ax_in, height=0.1, origin=(0,0), origin_br=True):
    # Calc extent
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


#add_draft(rdraft, (0,0), ax, size=0.2)
add_draft2(rdraft, ax, height=0.075)
ax.text(s="Chaos Esports", x=0, y=0.08,
        path_effects=[PathEffects.withStroke(linewidth=3,
                      foreground="w")],
        ha='left', va='bottom')
add_draft2(ddraft, ax, height=0.075, origin_br=False, origin=(1,1))
ax.text(s="Opposition", x=1.0, y=1.0 - 0.08,
        path_effects=[PathEffects.withStroke(linewidth=3,
                      foreground="w")],
        ha='right',
        va='top')
# plt.show()
plt.savefig("test.png", bbox_inches='tight')