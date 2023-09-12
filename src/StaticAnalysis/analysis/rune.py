from StaticAnalysis import session, team_session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import PlayerStatus
from StaticAnalysis.analysis.visualisation import plot_object_position, get_binning_percentile_xy
from StaticAnalysis.analysis.route_vis import plot_player_paths
from pandas import DataFrame
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.lib.Common import get_player_simple
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.lib.Common import add_map, EXTENT, prepare_retrieve_figure
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axis import Axis


def plot_player_positions(table: DataFrame, main_team: TeamInfo, fig: Figure):
    players = [p.player_id for p in main_team.players]
    names = [p.name for p in main_team.players]

    axes = fig.subplots(5, 2)
    axes[0][0].set_title("Dire")
    axes[0][1].set_title("Radiant")

    for p, n, a in zip(players, names, axes):
        dire_df = table.loc[(table['steamID'] == p) & (table['team'] == Team.DIRE)]
        vmin, vmax = get_binning_percentile_xy(dire_df)
        vmin = max(1.0, vmin)
        plot_object_position(
            dire_df,
            fig_in=fig,
            ax_in=a[0],
            vmin=vmin, vmax=vmax
        )
        a[0].axis('on')
        a[0].set_xticks([])
        a[0].set_yticks([])
        a[0].set_ylabel(n)

        radiant_df = table.loc[(table['steamID'] == p) & (table['team'] == Team.RADIANT)]
        vmin, vmax = get_binning_percentile_xy(radiant_df)
        vmin = max(1.0, vmin)
        plot_object_position(
            radiant_df,
            fig_in=fig,
            ax_in=a[1],
            vmin=vmin, vmax=vmax
        )
        a[1].axis('on')
        a[1].set_xticks([])
        a[1].set_yticks([])
        a[1].yaxis.set_label_position("right")
        a[1].set_ylabel(n)

    return axes


def plot_player_routes(table: DataFrame, main_team: TeamInfo, axis: Axis):
    colours = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple",
               "tab:brown", "tab:pink", "tab:gray", "tab:olive", "tab:cyan",]
    grp = table.groupby(['steamID', 'team_id']).agg({'xCoordinate': list, 'yCoordinate': list,
                                                     'team': 'first'})
    dire_positions = []
    radiant_positions = []
    if main_team.team_id not in table['team_id'].unique():
        print(f"Missing main team in {table['replayID'].iloc[0]}")

    for (p, t_id), c in zip(grp.index, colours):
        player = get_player_simple(p, team_session)
        if player:
            name = player.name
        else:
            name = p
        x = np.array(grp.xs((p, t_id))['xCoordinate'])
        y = np.array(grp.xs((p, t_id))['yCoordinate'])
        team = grp.xs((p, t_id))['team']
        plot = axis.quiver(x[:-1], y[:-1], x[1:] - x[:-1], y[1:] - y[:-1],
                           scale_units='xy', angles='xy', scale=1,
                           zorder=2, color=c, label=name)
        if team == Team.DIRE:
            dire_positions.append(plot)
        else:
            radiant_positions.append(plot)
    xMin, xMax, yMin, yMax = EXTENT
    axis.set_xlim(xMin, xMax)
    axis.set_ylim(yMin, yMax)
    axis.set_xticks([])
    axis.set_yticks([])

    # Create a legend for the first line.
    first_legend = axis.legend(handles=dire_positions, loc='upper right')
    # Add the legend manually to the current Axes.
    axis.add_artist(first_legend)
    # Create another legend for the second line.
    axis.legend(handles=radiant_positions, loc='lower left')

    return axis



# def plot_player_routes(table: DataFrame, main_team: TeamInfo, fig: Figure):
#     axis = fig.subplots()
#     add_map(axis, extent=EXTENT)
#     colours = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple",
#                "tab:brown", "tab:pink", "tab:gray", "tab:olive", "tab:cyan",]
#     # grp = table.groupby(['steamID', 'team_id']).agg({'xCoordinate': list, 'yCoordinate': list,
#     #                                                  'team': 'first'})
#     players_table = table.loc[:, ["steamID", "team"]].drop_duplicates()
#     dire_positions = []
#     radiant_positions = []
#     if main_team.team_id not in table['team_id'].unique():
#         print(f"Missing main team in {table['replayID'].iloc[0]}")

#     for (p, t), c in zip(players_table.itertuples(index=False, name=None), colours):
#         player = get_player_simple(p, team_session)
#         if player:
#             name = player.name
#         else:
#             name = p
#         filtered = table.loc[table['steamID'] == p, ['xCoordinate', 'yCoordinate']]
#         x = filtered.loc[:, 'xCoordinate'].to_numpy()
#         y = filtered.loc[:, 'yCoordinate'].to_numpy()
#         plot = axis.quiver(x[:-1], y[:-1], x[1:] - x[:-1], y[1:] - y[:-1],
#                            scale_units='xy', angles='xy', scale=1,
#                            zorder=2, color=c, label=name)
#         if t == Team.DIRE:
#             dire_positions.append(plot)
#         else:
#             radiant_positions.append(plot)
#     xMin, xMax, yMin, yMax = EXTENT
#     axis.set_xlim(xMin, xMax)
#     axis.set_ylim(yMin, yMax)
#     axis.set_xticks([])
#     axis.set_yticks([])

#     # Create a legend for the first line.
#     first_legend = axis.legend(handles=dire_positions, loc='upper right')
#     # Add the legend manually to the current Axes.
#     axis.add_artist(first_legend)
#     # Create another legend for the second line.
#     axis.legend(handles=radiant_positions, loc='lower left')

#     return axis