import Setup
import os
import sys
from os import environ as environment
from typing import List
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.Common import get_team
from replays.Replay import Replay, Team
from analysis.Replay import get_ptbase_tslice, get_ptbase_tslice_side
from replays.Ward import Ward, WardType 
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()
load_dotenv(dotenv_path="../test.env")

# teamName = "Royal Never Give Up"
teamName = "Hippomaniacs"
team = get_team(team_session, teamName)
# Royal never give up test case for bad pos
# r_query = team.get_replays(session).filter(Replay.replayID == 4857623860)
r_query = team.get_replays(session).filter(Replay.replayID == 4901403209)
d_query = team.get_replays(session)
#d_query = team.get_replays(session).filter(Replay.replayID == 4901517396)
wards_radiant = get_ptbase_tslice_side(session, r_query, team=team,
                                       Type=Ward,
                                       side=Team.RADIANT,
                                       start=-2*60, end=20*60)
wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)
wards_dire, _ = get_ptbase_tslice(session, d_query, team=team,
                                  Type=Ward,
                                  start=-2*60, end=20*60)
wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)


from analysis.ward_vis import build_ward_table
data = build_ward_table(wards_radiant, session, team_session, team)
ddata = build_ward_table(wards_dire, session, team_session, team)
from analysis.ward_vis import plot_full_text, plot_num_table, plot_eye_scatter, plot_drafts, plot_drafts_above

fig, ax = plt.subplots(figsize=(10, 13))
plot_full_text(data, ax)
# plot_drafts(r_query, ax, r_name=teamName)
# fig.savefig("r_full_text.png", bbox_inches='tight')

# fig, ax = plt.subplots(figsize=(10, 13))
# plot_full_text(ddata, ax)
# plot_drafts(d_query, ax, d_name=teamName)
# fig.savefig("d_full_text.png", bbox_inches='tight')

# fig, ax = plt.subplots(figsize=(10, 13))
# plot_num_table(data, ax)
# plot_drafts(r_query, ax, r_name=teamName)
# fig.savefig("r_table.png", bbox_inches='tight')

# fig, ax = plt.subplots(figsize=(10, 13))
# plot_num_table(ddata, ax)
# plot_drafts(d_query, ax, d_name=teamName)
# fig.savefig("d_table.png", bbox_inches='tight')

# fig, ax = plt.subplots(figsize=(10, 13))
# plot_eye_scatter(data, ax)
# plot_drafts(r_query, ax, r_name=teamName)
# fig.savefig("eye_large.png", bbox_inches='tight')

# fig, ax = plt.subplots(figsize=(10, 13))
# plot_eye_scatter(data, ax, size=(12, 9))
# plot_drafts(r_query, ax, r_name=teamName)
# fig.savefig("eye_small.png", bbox_inches='tight')


# https://stackoverflow.com/questions/19306510/determine-matplotlib-axis-size-in-pixels
def get_ax_size(ax_in, fig_in):
    bbox = ax_in.get_window_extent()\
                .transformed(fig_in.dpi_scale_trans.inverted())
    width, height = bbox.width, bbox.height
    width *= fig_in.dpi
    height *= fig_in.dpi
    return width, height

fig, ax = plt.subplots(figsize=(10, 13))
width, height = get_ax_size(ax, fig)
extras = plot_eye_scatter(data, ax, size=(18, 14))
drafts = plot_drafts_above(r_query, ax, width, r_name=teamName)
#fig.savefig("r_eye_med.png", bbox_inches='tight')
fig.savefig("r_eye_med.png", bbox_extra_artists=(*drafts, *extras), bbox_inches='tight')

# fig, ax = plt.subplots(figsize=(10, 13))
# plot_eye_scatter(ddata, ax, size=(18, 14))
# plot_drafts(d_query, ax, d_name=teamName)
# fig.savefig("d_eye_med.png", bbox_inches='tight')