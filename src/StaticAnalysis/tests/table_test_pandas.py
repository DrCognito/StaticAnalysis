import os
import sys
from typing import Tuple


import StaticAnalysis.tests.minimal_db as db
from StaticAnalysis.replays.Player import Player
from StaticAnalysis.replays.TeamSelections import PickBans, TeamSelections

from StaticAnalysis.lib.team_info import TeamInfo

import matplotlib.pyplot as plt

from os import environ as environment
from dotenv import load_dotenv
from StaticAnalysis.analysis.ward_vis import colour_list, plot_labels
from pandas import DataFrame, Interval, IntervalIndex, cut, read_sql
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.lib.Common import seconds_to_nice, get_player_map,get_player_name
from herotools.important_times import ImportantTimes, MAIN_TIME
from StaticAnalysis.analysis.visualisation import make_image_annotation_flex, make_image_annotation, make_image_annotation_table
from itertools import cycle
from herotools.HeroTools import HeroIconPrefix, HeroIDType, convertName, heroShortName
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont
from math import ceil, floor
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm.query import Query
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import io
import numpy as np

og_id = 2586976
entity = 8605863
psg = 15
team_id = og_id
time = MAIN_TIME
time = ImportantTimes['Patch_7_34']
team: TeamInfo = db.get_team(team_id)
r_query = team.get_replays(db.session).filter(Replay.endTimeUTC >= time)

q_test = (db.session.query(PickBans)
                    .filter(PickBans.is_pick == True)
                    .filter(PickBans.teamID == team_id)
                    .join(r_query.subquery()))

from sqlalchemy import or_
first_selection = (
    db.session.query(TeamSelections)
      .filter(team.custom_filter(TeamSelections.teamID, TeamSelections.stackID))
      .filter(TeamSelections.firstPick == True)
      .join(r_query.subquery())
)
second_selection = (
    db.session.query(TeamSelections)
      .filter(team.custom_filter(TeamSelections.teamID, TeamSelections.stackID))
      .filter(TeamSelections.firstPick == False)
      .join(r_query.subquery())
)
from sqlalchemy.orm import contains_eager
from sqlalchemy import and_
# second_selection_pb = (
#     db.session.query(PickBans)
#       .join(TeamSelections, and_(TeamSelections.replay_ID == PickBans.replayID, TeamSelections.team == PickBans.team))
#       .options(contains_eager(TeamSelections.draft))
#       .filter(team.custom_filter(TeamSelections.teamID, TeamSelections.stackID))
#       .filter(TeamSelections.firstPick == False)
#       .join(r_query.subquery())
# )
fq = first_selection.subquery()
first_selection_pb = (
    db.session.query(PickBans)
      .filter(PickBans.is_pick == True)
      .join(fq, and_(fq.c.replay_ID == PickBans.replayID, fq.c.team == PickBans.team))
)
sq = second_selection.subquery()
second_selection_pb = (
    db.session.query(PickBans)
      .filter(PickBans.is_pick == True)
      .join(sq, and_(sq.c.replay_ID == PickBans.replayID, sq.c.team == PickBans.team))
)

@dataclass
class OrderTimeRegion:
    start: datetime
    first_pick: list
    second_pick: list
    end: datetime = None

picks_patch_7_34 = OrderTimeRegion(ImportantTimes['Patch_7_34'],
                                   [8, 14, 15, 18, 23],
                                   [9, 13, 16, 17, 24],
                                   None)


df = read_sql(q_test.statement, db.session.bind)
firstp_df = read_sql(first_selection_pb.statement, db.session.bind)
secondp_df = read_sql(second_selection_pb.statement, db.session.bind)

# Pick patterns that do not match
print(firstp_df[~firstp_df['order'].isin(picks_patch_7_34.first_pick)])
print(secondp_df[~secondp_df['order'].isin(picks_patch_7_34.second_pick)])


def verify_fix_order(df_in: DataFrame, order: list):
    broken = df_in.loc[~df_in['order'].isin(order)]
    if broken.empty:
        return
    r_ids = broken.loc[:, 'replayID'].unique()
    print(f"Broken pick ban pattern in: {r_ids}")

    for r in r_ids:
        section = df_in.loc[df_in['replayID'] == r, 'order']
        # Limit to the length of the part
        df_in.loc[df_in['replayID'] == r, 'order'] = order[:len(section)]

    return
# firstp_df = verify_fix_order(firstp_df, picks_patch_7_34.first_pick)
# secondp_df = verify_fix_order(secondp_df, picks_patch_7_34.first_pick)

verify_fix_order(firstp_df, picks_patch_7_34.first_pick)
verify_fix_order(secondp_df, picks_patch_7_34.second_pick)

from pandas import concat
pick_df = concat([firstp_df, secondp_df], ignore_index=True)

from collections import Counter
count_df = pick_df.groupby(['playerID', 'order']).agg({'hero':Counter})
from pandas import pivot_table
# This provides a more natural representation, moving the order out to columns
rotatioed = pivot_table(pick_df, index='playerID', columns='order', values='hero', aggfunc=Counter, fill_value=Counter())