from StaticAnalysis import Session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import PlayerStatus
from StaticAnalysis.analysis.visualisation import plot_player_positioning
from StaticAnalysis.analysis.route_vis import plot_player_paths
from pandas import DataFrame
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.lib.Common import get_player_simple
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.lib.Common import add_map, EXTENT

def plot_player_positions(table: DataFrame, main_team: TeamInfo, fig: Figure):
    players = [p.player_id for p in main_team.players]
    names = [p.name for p in main_team.players]

    axes = fig.subplots(5, 2)
    axes[0][0].set_title("Dire")
    axes[0][1].set_title("Radiant")

    for p, n, a in zip(players, names, axes):
        plot_player_positioning(
            table[(table['steamID'] == p) & (table['team'] == Team.DIRE)],
            a[0]
        )
        a[0].set_ylabel(n)
        plot_player_positioning(
            table[(table['steamID'] == p) & (table['team'] == Team.RADIANT)],
            a[1]
        )
        a[1].ax_in.yaxis.set_label_position("right")
        a[1].set_ylabel(n)

    return axes


def plot_player_routes(table: DataFrame, main_team: TeamInfo, fig: Figure):
    axis = fig.subplots()
    add_map(axis, extent=EXTENT)
    colours = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple",
               "tab:brown", "tab:pink", "tab:gray", "tab:olive", "tab:cyan",]
    grp = table.groupby(['steamID', 'team_id']).agg({'xCoordinate': list, 'yCoordinate': list,
                                                     'team': 'first'})
    dire_positions = []
    radiant_positions = []
    assert main_team.team_id in table['team_id'].unique()
    for p, t_id, c in zip(table.index, colours):
        player = get_player_simple(p)
        if player:
            name = player.name
        else:
            name = p
        x = grp.xs(p, t_id)['xCoordinate']
        y = grp.xs(p, t_id)['yCoordinate']
        team = grp.xs(p, t_id)['team']
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

    # Create a legend for the first line.
    first_legend = axis.legend(handles=dire_positions, loc='upper right')
    # Add the legend manually to the current Axes.
    axis.add_artist(first_legend)
    # Create another legend for the second line.
    axis.legend(handles=radiant_positions, loc='lower left')

    return axis


# def plot_player_paths(paths, colours, names, axis):
#     assert(len(paths) <= len(colours))
#     # add_map(axis)
#     plots = []
#     for colour, path, name in zip(colours, paths, names):
#         if path.empty:
#             continue
#         x = path['xCoordinate'].to_numpy()
#         y = path['yCoordinate'].to_numpy()

#         plot = axis.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1],
#                            scale_units='xy', angles='xy', scale=1,
#                            zorder=2, color=colour, label=name)
#         plots.append(plot)
#         axis.axis('off')
#     xMin, xMax, yMin, yMax = EXTENT
#     axis.set_xlim(xMin, xMax)
#     axis.set_ylim(yMin, yMax)

#     return plots