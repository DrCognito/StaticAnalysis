import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import minimal_db as db
from dotenv import load_dotenv
from os import environ as environment
from lib.team_info import TeamInfo
from replays.Replay import InitDB, Replay, Team
from lib.important_times import ImportantTimes
from analysis.Player import player_position
import time
from lib.Common import (dire_ancient_cords, location_filter, radiant_ancient_cords)
from replays.Player import PlayerStatus
from analysis.visualisation import dataframe_xy, get_binning_percentile_xy, plot_object_position
import matplotlib.pyplot as plt


load_dotenv(dotenv_path="setup.env")
SCRIMS_JSON_PATH = environment['SCRIMS_JSON']
TEAMS_JSON_PATH = environment['SCRIMS_TEAMS']
main_team_id = 2586976
main_team_name = "OG"

main_team: TeamInfo = db.get_team(main_team_id)

first_id = 6447830786
last_id = 6647289573
r_time = ImportantTimes['Patch_7_31']
# r_filter = Replay.endTimeUTC >= time
# Fixed ids for fixed benchmarks!
r_filter = ((Replay.replayID >= first_id) & (Replay.replayID <= last_id))
r_query = main_team.get_replays(db.session).filter(r_filter)

fig, axes = plt.subplots(1, 2, figsize=(15, 10))


def run_player(pos: int):
    start_time = -2*60
    end_time = 10*60
    # Get the data
    (dire, dire_limited), \
        (radiant, radiant_limited) = player_position(db.session, r_query,
                                                    main_team, pos, start_time,
                                                    end_time)
    # Ancient filters
    dire_ancient_filter = location_filter(dire_ancient_cords, PlayerStatus)
    dire = dire.filter(dire_ancient_filter)
    dire_limited = dire_limited.filter(dire_ancient_filter)

    radiant_ancient_filter = location_filter(radiant_ancient_cords, PlayerStatus)
    radiant = radiant.filter(radiant_ancient_filter)
    radiant_limited = radiant_limited.filter(radiant_ancient_filter)

    # Get DataFrames
    pos_dire_df = dataframe_xy(dire, PlayerStatus, db.session)
    pos_dire_limited_df = dataframe_xy(dire_limited, PlayerStatus, db.session)
    pos_radiant_df = dataframe_xy(radiant, PlayerStatus, db.session)
    pos_radiant_limited_df = dataframe_xy(radiant_limited, PlayerStatus, db.session)

    # Plots
    vmin, vmax = get_binning_percentile_xy(pos_dire_df)
    plot_object_position(pos_dire_df,
                         bins=64, fig_in=fig, ax_in=axes[0],
                         vmin=vmin, vmax=vmax)

    vmin, vmax = get_binning_percentile_xy(pos_dire_limited_df)
    plot_object_position(pos_dire_limited_df,
                         bins=64, fig_in=fig, ax_in=axes[1],
                         vmin=vmin, vmax=vmax)

    vmin, vmax = get_binning_percentile_xy(pos_radiant_df)
    plot_object_position(pos_radiant_df,
                         bins=64, fig_in=fig, ax_in=axes[0],
                         vmin=vmin, vmax=vmax)

    vmin, vmax = get_binning_percentile_xy(pos_radiant_limited_df)
    plot_object_position(pos_radiant_limited_df,
                         bins=64, fig_in=fig, ax_in=axes[1],
                         vmin=vmin, vmax=vmax)


perf_start = time.perf_counter()
for i in range(5):
    run_player(i)
print(f"Completed Execution in {time.perf_counter() - perf_start} seconds")