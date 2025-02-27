from StaticAnalysis import session, team_session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.Player import PlayerStatus
from StaticAnalysis.replays.Rune import Rune, RuneID
from StaticAnalysis.analysis.visualisation import plot_object_position, get_binning_percentile_xy
from StaticAnalysis.analysis.route_vis import plot_player_paths
from pandas import DataFrame
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from StaticAnalysis.lib.Common import get_player_simple, seconds_to_nice
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from StaticAnalysis.replays.Common import Team
from StaticAnalysis.lib.Common import EXTENT, convert_to_32_bit, get_closest_ancient
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axis import Axis
import matplotlib.patheffects as PathEffects
from pandas import read_sql
from sqlalchemy.orm import Session
from StaticAnalysis.lib.team_info import get_player
from StaticAnalysis.analysis.Player import map_player_location_time, get_player_hero


def wisdom_rune_times(r_query, max_time: int, session=session, extra_filter: tuple = None) -> DataFrame:
    rune_query = (    
        session.query(Rune.game_time, Rune.replayID)
               .join(r_query.subquery())
               .filter(Rune.runeType == RuneID.Wisdom, Rune.game_time < max_time)
    )

    return read_sql(rune_query.statement, session.bind)


def wisdom_rune_table(r_query, max_time: int, session=session, extra_filter: tuple = None) -> DataFrame:
    rune_query = (    
        session.query(Rune, Rune.game_time)
               .join(r_query.subquery())
               .filter(Rune.runeType == RuneID.Wisdom, Rune.game_time < max_time)
    )

    return read_sql(rune_query.statement, session.bind)


def build_wisdom_rune_summary(
    rune_table: DataFrame, team_session: Session = team_session,):
    def _name(pid: int):
        player: TeamPlayer = get_player(pid, team_session)
        if player is not None:
            return player.name
        else:
            return convert_to_32_bit(pid)
    # Build the new columns
    rune_table['Name'] = rune_table['steamID'].map(_name)
    rune_table['xCoordinate'], rune_table['yCoordinate'] = map_player_location_time(
        rune_table['game_time'], rune_table['steamID'], rune_table['replayID']
        )
    rune_table['rune_loc'] = rune_table.apply(
        lambda x: get_closest_ancient(x['xCoordinate'], x['yCoordinate']), axis=1
        )
    rune_table['StolenB'] = rune_table['team'] != rune_table['rune_loc']
    rune_table['hero'] = rune_table.apply(
        lambda x: get_player_hero(x['steamID'], x['replayID']), axis=1
    )
    rune_table['nice_time'] = rune_table['game_time'].map(seconds_to_nice)
    # Polish for export
    # Convert Stolen to text
    rune_table.loc[:,'Stolen'] = rune_table.loc[:,'StolenB'].map({True:'yes', False:'no'}).astype(str)
    # Convert rune_loc to text
    rune_table.loc[:,'rune_loc'] = rune_table.loc[:,'rune_loc'].map({Team.DIRE:'Dire', Team.RADIANT:'Radiant'})
    columns = ['replayID','nice_time', 'rune_loc', 'Name', 'hero', 'Stolen']
    return rune_table.loc[:, columns]


def plot_wisdom_table(df: DataFrame, axe):
    table = axe.table(
        cellText=df.values,
        loc='bottom',
        # colWidths=[0.05, 0.2, 0.1, 0.15, 0.05, 0.2, 0.1, 0.15],
        colLabels=["Time", "Rune Side", "Player", "Hero", "Stolen?"])
    
    return axe

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
    colours = ["tab:blue", "tab:orange", "yellow", "tab:red", "tab:purple",
               "lime", "tab:pink", "black", "tab:olive", "tab:cyan",]
    grp = table.groupby(['steamID', 'team_id']).agg({'xCoordinate': list, 'yCoordinate': list,
                                                     'team': 'first'})
    # Sometimes replays have nothing1
    if table.empty:
        return axis

    dire_positions = []
    radiant_positions = []
    replay_id = table['replayID'].iloc[0]
    if main_team.team_id not in table['team_id'].unique():
        print(f"Missing main team in {replay_id}")

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

    axis.text(s=str(replay_id), x=1.0, y=0,
            ha='right', va='bottom', zorder=5,
            path_effects=[PathEffects.withStroke(linewidth=3,
                          foreground="w")],
            color='black',
            transform=axis.transAxes)

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