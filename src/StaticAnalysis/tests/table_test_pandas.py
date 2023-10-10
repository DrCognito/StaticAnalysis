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

og_id = 2586976
entity = 8605863
psg = 15
team_id = og_id
time = MAIN_TIME
team = db.get_team(team_id)
r_query = team.get_replays(db.session).filter(Replay.endTimeUTC >= time)

q_test = (db.session.query(PickBans)
                    .filter(PickBans.is_pick == True)
                    .filter(PickBans.teamID == team_id)
                    .join(r_query.subquery()))


@dataclass
class OrderTimeRegion:
    start: datetime
    first_pick: list
    second_pick: list
    end: datetime = None


df = read_sql(q_test.statement, db.session.bind)