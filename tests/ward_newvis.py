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
from pandas import DataFrame, read_sql, Series
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.image as mpimg
from dotenv import load_dotenv
from datetime import timedelta
from math import sin, cos, radians
import matplotlib.patheffects as PathEffects
from adjustText import adjust_text
from analysis.draft_vis import hero_box_image, process_team
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()
load_dotenv(dotenv_path="../test.env")


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
teamName = "Royal Never Give Up"
team = get_team(teamName)
r_query = team.get_replays(session).filter(Replay.replayID == 4857623860)
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


# def get_clusters(data: DataFrame, clusters=4) -> List[int]:
#     kmeans = KMeans(n_clusters=clusters)
#     kmeans.fit(data[['xCoordinate', 'yCoordinate']].values)
#     print(kmeans.cluster_centers_)
#     return kmeans.labels_


# def plot_overlayed_smokes(data: DataFrame, ax_in):
#     # Pre game to 20mins
#     vmin = -120
#     vmax = 20*60
#     jet = plt.get_cmap('afmhot')

#     img = mpimg.imread(environment['MAP_PATH'])
#     ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
#     ax_in.axis('off')
#     ax_in.set_xlim(0, 1)
#     ax_in.set_ylim(0, 1)

#     smoke_data = data.loc[data["anon_1"] == True]
#     normal_data = data.loc[data["anon_1"] == False]
#     data = data.sort_values(by='game_time', ascending=False)

#     # ax_in.scatter(x=smoke_data['xCoordinate'],
#     #               y=smoke_data['yCoordinate'],
#     #               y=smoke_data['game_time'],
#     #               edgecolor='gray', linewidth='3',
#     #               vmin=vmin, vmax=vmax)

#     # ax_in.scatter(x=smoke_data['xCoordinate'],
#     #               y=smoke_data['yCoordinate'],
#     #               c=smoke_data['game_time'],
#     #               edgecolor='grey', linewidth=3,
#     #               marker='1',
#     #               s=250, cmap='gist_rainbow',
#     #               alpha=0.75,
#     #               vmin=vmin, vmax=vmax,
#     #               zorder=3)

#     # ax_in.scatter(x=normal_data['xCoordinate'],
#     #               y=normal_data['yCoordinate'],
#     #               c=normal_data['game_time'],
#     #               edgecolor='g', linewidth=3,
#     #               s=250, cmap='gist_rainbow',
#     #               alpha=0.75, marker='2',
#     #               vmin=vmin, vmax=vmax,
#     #               zorder=2)

#     # table_test = data[['Initials', 'game_time']][0:3]
#     # ax_in.table(cellText=table_test.values,
#     #             rowLabels=table_test.index,
#     #             colLabels=table_test.columns,
#     #             bbox=[0, 0, 0.2, 0.05], zorder=2)
#     # ax_in.table(cellText=table_test.values,
#     #             rowLabels=table_test.index,
#     #             colLabels=table_test.columns,
#     #             loc='top')

#     data['clusters'] = get_clusters(data)
#     cluster_info = data.groupby(['clusters',])['xCoordinate'].nunique()
#     cluster_tots = cluster_info.to_dict()

#     texts = []
#     for j, row in data.iterrows():
#         texts.append(text_point(row, ax_in))

#     adjust_text(texts, ax=ax_in,
#                 va='bottom',
#                 ha='left',
#                 arrowprops=dict(arrowstyle='->', color='r', lw=2),)


def plot_adjusted_text(data: DataFrame, ax_in,
                       text_kwargs={}, arrow_kwargs=None):
    text_items = []
    for i, text in data['label'].iteritems():
        txt = ax_in.text(x=data['xCoordinate'][i], y=data['yCoordinate'][i],
                         s=text,
                         **text_kwargs)
        text_items.append(txt)

    if arrow_kwargs is not None:
        adjust_text(text_items, ax=ax_in,
                    va='bottom',
                    ha='left',
                    arrowprops=arrow_kwargs,)
    else:
        adjust_text(text_items, ax=ax_in,
                    va='bottom',
                    ha='left',)

    return text_items


def plot_adjusted_text_extras(data: DataFrame, ax_in,
                              extra_ents,
                              text_kwargs={}, arrow_kwargs=None):
    text_items = []
    for i, text in data['label'].iteritems():
        txt = ax_in.text(x=data['xCoordinate'][i], y=data['yCoordinate'][i],
                         s=text,
                         **text_kwargs,
                         zorder=10)
        text_items.append(txt)

    if arrow_kwargs is not None:
        adjust_text(text_items, ax=ax_in,
                    va='bottom',
                    ha='left',
                    add_objects=extra_ents,
                    arrowprops=arrow_kwargs,)
    else:
        adjust_text(text_items, ax=ax_in,
                    va='bottom',
                    ha='left',
                    add_objects=extra_ents,)

    return text_items


def plot_full_text(data: DataFrame, ax_in):
    labels = []
    for _, row in data.iterrows():
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

        labels.append(text)
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')
    ax_in.set_xlim(0, 1)
    ax_in.set_ylim(0, 1)
    data['label'] = labels
    text_style = {'color':'blue',
                  'va':'bottom',
                  'ha':'left',
                  'path_effects':[PathEffects.withStroke(linewidth=3,
                   foreground="w")]}
    arrow_style = dict(arrowstyle='->', color='r', lw=2)
    plot_adjusted_text(data, ax_in, text_style, arrow_style)


def plot_num_table(data: DataFrame, ax_in):
    data['label'] = [str(x + 1) for x in range(data.shape[0])]
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')
    ax_in.set_xlim(0, 1)
    ax_in.set_ylim(0, 1)

    text_style = {'color':'blue',
                  'va':'bottom',
                  'ha':'left',
                  'path_effects':[PathEffects.withStroke(linewidth=3,
                   foreground="w")],
                   'fontsize':14}
    arrow_style = dict(arrowstyle='-', color='r', lw=2)
    plot_adjusted_text(data, ax_in, text_style, arrow_style)
    # Plot first 6
    out_table = DataFrame()
    out_table['label'] = data['label'][:6]
    out_table['Name'] = data['Name'][:6]
    out_table['time'] = data['time'][:6]
    out_table['smoked'] = data['anon_1'][:6]
    out_table['label2'] = data['label'][6:].reset_index()['label']
    out_table['Name2'] = data['Name'][6:].reset_index()['Name']
    out_table['time2'] = data['time'][6:].reset_index()['time']
    out_table['smoked2'] = data['anon_1'][6:].reset_index()['anon_1']
    out_table['smoked2'] = out_table['smoked2'].map({True: 'Y', False: 'N'})
    out_table['smoked'] = out_table['smoked'].map({True: 'Y', False: 'N'})
    out_table = out_table.apply(lambda x: Series(x.dropna().values))
    out_table.fillna(value='', inplace=True)

    tab = ax_in.table(cellText=out_table.values,
                      loc='bottom',
                      colWidths=[0.05,0.2,0.1,0.15,0.05,0.2,0.1,0.15],
                      colLabels=["", "Name", "Time", "Smoked",
                                 "", "Name", "Time", "Smoked"])


def plot_eye_scatter_full(data: DataFrame, ax_in):
    labels = []
    for _, row in data.iterrows():
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

        labels.append(text)

    data['label'] = labels
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=[0, 1, 0, 1], zorder=0)
    ax_in.axis('off')
    ax_in.set_xlim(0, 1)
    ax_in.set_ylim(0, 1)

    # Display wards
    ward = Image.open('E:/Python/StaticAnalysis/img/Observer_Ward_minimap_icon_green.png')
    ward.thumbnail((14, 34), Image.ANTIALIAS)

    def _plot_eyes():
        img_boxes = []
        for _, row in data.iterrows():
            imagebox = OffsetImage(ward)
            imagebox.image.axes = ax_in
            pos = (row['xCoordinate'], row['yCoordinate'])
            ab = AnnotationBbox(imagebox, pos,
                        xycoords='data',
                        boxcoords="offset points",
                        box_alignment=(0.5,0.5),
                        pad=0,
                        frameon=False
                        )
            ax_in.add_artist(ab)
            ab.set_zorder(2)
            img_boxes.append(ab)
        return img_boxes

    extra_ents = _plot_eyes()
    print(extra_ents)
    text_style = {'color':'blue',
                  'va':'bottom',
                  'ha':'left',
                  'path_effects':[PathEffects.withStroke(linewidth=3,
                   foreground="w")]}
    arrow_style = dict(arrowstyle='-', color='black', lw=1)
    plot_adjusted_text_extras(data, ax_in, extra_ents, text_style, arrow_style)

#plot_overlayed_smokes(data, ax)
#plot_full_text(data, ax)
#plot_num_table(data, ax)
plot_eye_scatter_full(data, ax)
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
ax.text(s=teamName, x=0, y=0.08,
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