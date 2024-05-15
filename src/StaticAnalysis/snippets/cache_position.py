from matplotlib.collections import PolyCollection
from StaticAnalysis.snippets.minimal_db import session, team_session, team
from StaticAnalysis.replays.Replay import Replay
from herotools.important_times import MAIN_TIME
from StaticAnalysis.analysis.Player import player_position, PlayerStatus
from StaticAnalysis.analysis.visualisation import dataframe_xy, get_binning_percentile_xy, plot_object_position
import matplotlib.pyplot as plt
from pandas import DataFrame, cut
from StaticAnalysis.lib.Common import EXTENT
from StaticAnalysis.lib.team_info import TeamInfo, TeamPlayer
from pathlib import Path
from StaticAnalysis.replays.Replay import Replay, Team
import pickle
from os import environ as environment


r_filter = Replay.endTimeUTC >= MAIN_TIME
r_query = team.get_replays(session).filter(r_filter)
position = 0 # Choses the player in team
recent_limit = 5
start = -2*60
end = 10*60

CACHE_ROOT = Path(environment["CACHE"])

def player_position_single(
    session, r_query,
    team: TeamInfo, player: TeamPlayer,
    side: Team,
    start: int, end: int, recent_limit=None):

    t_filter = ()
    if start is not None:
        t_filter += (PlayerStatus.game_time >= start,)
    if end is not None:
        t_filter += (PlayerStatus.game_time <= end,)

    steam_id = player.player_id

    r_filter = Replay.get_side_filter(team, side)
    replays = r_query.filter(r_filter).subquery()
    if recent_limit is not None:
        replays = r_query.filter(r_filter).order_by(Replay.replayID.desc()).limit(recent_limit).subquery()

    p_filter = t_filter + (PlayerStatus.steamID == steam_id,
                            PlayerStatus.team == side)

    player_q = session.query(PlayerStatus)\
                        .filter(*p_filter)\
                        .join(replays)

    return player_q

# [[xmin, xmax], [ymin, ymax]]
extent_numpy = [[EXTENT[0], EXTENT[1]], [EXTENT[2], EXTENT[3]]]
import numpy as np
import json
import pickle

class CachePositioning():
    # Sentinels
    EMPTY_CACHE = object()
    INVALID_CACHE = object()
    def __init__(self, side: Team, team: TeamInfo) -> None:
        self.side: Team = side
        self.team: TeamInfo = team
        # Dictionaries for each player
        # Replay list can be player specific if people leave/join!
        self.replay_list = {}
        self.positions = {}
        self.xedges = {}
        self.yedges = {}

    def valid_cache(self, r_query, player: TeamPlayer) -> bool:
        '''
        Compares the replay list in the cache with that of r_query for a TeamPlayer.
        Returns True if all replays in cache exist in r_query for this team.
        Returns False otherwise or if empty.
        '''
        cached_replays = self.replay_list.get(pid:=player.player_id, set())
        if len(cached_replays) == 0:
            return False

        if any(
            pid not in self.positions,
            pid not in self.xedges,
            pid not in self.yedges
            ):
            return False

        replay_set = {r.replayID for r in r_query}
        return cached_replays in replay_set

    def get_reduced_query(self, r_query, player: TeamPlayer):
        '''
        Given the cached results for TeamPlayer, provide a query that only has the remainder.
        '''
        if not self.valid_cache(r_query, player):
            return r_query

        cached_replays = self.replay_list.get(pid:=player.player_id, set())
        replay_set = {r.replayID for r in r_query}
        return r_query.filter(Replay.replayID.in_(replay_set - cached_replays))
def get_binned_positioning(
        session,
        r_query,
        team: TeamInfo,
        player: TeamPlayer,
        side: Team,
        start: int,
        end: int,
        cache_id: str,
        limit: int =  None,
        use_cache: bool = True
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Only interested in one side
    r_query = r_query.filter(Replay.get_side_filter(team, side))
    side_name = "dire" if side == Team.DIRE else "radiant"
    # Load cache
    cache_path = CACHE_ROOT / "positioning" / f"{cache_id}"
    cache = CachePositioning(side, team)
    if use_cache and cache_path.exists():
        with open(cache_path, 'r') as cache_f:
            cache = pickle.load(cache_path)
    # Use the cache to get a restricted query
    r_query = cache.get_reduced_query(r_query, player)
    # Retrieve data
    p_query = player_position_single(
        session, r_query,
        team, player,
        side,
        start, end, recent_limit=limit
    )
    positioning = dataframe_xy(p_query, PlayerStatus, session)
    # Bin data
    if not positioning.empty:
        # New results
        position_new, xedge_new, yedge_new = np.histogram2d(
        x=positioning['xCoordinate'],
        y=positioning['yCoordinate'],
        bins=64,
        range=extent_numpy
        )
    elif position_cache is None:
        # No results at all
        print(f"No cache or results for {player.name}/{player.player_id}")
        return None, None, None
    else:
        # No new results, just cache
        return (
            position_cache,
            xedge_cache,
            yedge_cache,
            )

    # Combine
    xedges = xedge_new
    yedges = yedge_new
    if position_cache is None:
        positions = position_new
    else:
        positions = position_new + position_cache
    # Cache
    if use_cache:
        cache_json["replays"] = list(replay_set)
        player_cache["positions"] = pickle.dumps(positions)
        player_cache["xedges"] = pickle.dumps(xedges)
        player_cache["yedges"] = pickle.dumps(yedges)
        cache_json[player.player_id] = player_cache
        with open(cache_path, 'w') as cache_f:
            json.dump(cache_json, cache_f)
    # Return
    return positions, xedges, yedges


((pos_dire, pos_dire_limited),
(pos_radiant, pos_radiant_limited)) = player_position(
                                                      session,
                                                      r_query,
                                                      team,
                                                      player_slot=position,
                                                      start=start, end=end,
                                                      recent_limit=recent_limit)
# Normal method
pos_dire_df = dataframe_xy(pos_dire, PlayerStatus, session)
pos_dire_limited_df = dataframe_xy(pos_dire_limited, PlayerStatus, session)

fig, axes = plt.subplots(1, 2, figsize=(15, 10))

# vmin, vmax = get_binning_percentile_xy(pos_dire_df)
# vmin = max(1.0, vmin)
# axis = plot_object_position(pos_dire_df,
#                             bins=64, fig_in=fig, ax_in=axes[0],
#                             vmin=vmin, vmax=vmax)

# vmin, vmax = get_binning_percentile_xy(pos_dire_limited_df)
# vmin = max(1.0, vmin)
# axis = plot_object_position(pos_dire_limited_df,
#                             bins=64, fig_in=fig, ax_in=axes[1],
#                             vmin=vmin, vmax=vmax)
# axis.set_title('Latest 5 games')

# fig.tight_layout()
# fig.savefig("timado_pos_default.png", bbox_inches='tight')

def bin_pos_data(df: DataFrame, bins=64, extent=EXTENT):
    binning = [float(x) / bins for x in range(bins)]

    xExtent = float(abs(extent[1] - extent[0]))
    xBins = [extent[0] + x * xExtent for x in binning]

    yExtent = float(abs(extent[3] - extent[2]))
    yBins = [extent[2] + y * yExtent for y in binning]

    # with ChainedAssignment():
    df['xBin'] = cut(df['xCoordinate'], xBins)
    df['yBin'] = cut(df['yCoordinate'], yBins)

    df = df.groupby(['xBin', 'yBin'], observed=True, as_index=False)[['xCoordinate']].count()
    df['xBin'] = df['xBin'].apply(lambda x: x.mid)
    df['yBin'] = df['yBin'].apply(lambda x: x.mid)

    return df

import copy
from os import environ as environment
import matplotlib.image as mpimg
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import ticker
def plot_counts_hexbin(query_data: DataFrame, bins=64,
                fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = ax_in.hexbin(x=query_data['xBin'],
                            y=query_data['yBin'],
                            C=query_data['xCoordinate'],
                            gridsize=bins, mincnt=0,
                            extent=EXTENT,
                            cmap=colour_map,
                            vmin=vmin, vmax=vmax,
                            zorder=2)
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot, cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in


def get_hexbin_binning(pollies: PolyCollection):
    pass

def plot_counts_hist2d(query_data: DataFrame, bins=64,
                fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        # plot = ax_in.hexbin(x=query_data['xBin'],
        #                     y=query_data['yBin'],
        #                     C=query_data['xCoordinate'],
        #                     gridsize=bins, mincnt=0,
        #                     extent=EXTENT,
        #                     cmap=colour_map,
        #                     vmin=vmin, vmax=vmax,
        #                     zorder=2)
        plot = ax_in.hist2d(x=query_data['xBin'],
                            y=query_data['yBin'],
                            weights=query_data['xCoordinate'],
                            bins=bins,
                            # extent=EXTENT,
                            range=[[EXTENT[0], EXTENT[1]], [EXTENT[2], EXTENT[3]]],
                            cmap=colour_map,
                            cmin=vmin, cmax=vmax,
                            zorder=2)
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot[3], cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in


def plot_counts_pcolormesh(
    query_data: DataFrame, bins=64,
    fig_in=None, ax_in=None,
    vmin=1):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # [[xmin, xmax], [ymin, ymax]]
    extent_numpy = [[EXTENT[0], EXTENT[1]], [EXTENT[2], EXTENT[3]]]
    vals, xedges, yedges = np.histogram2d(
        x=query_data['xCoordinate'],
        y=query_data['yCoordinate'],
        bins=64,
        range=extent_numpy
    )
    X, Y = np.meshgrid(xedges, yedges)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = ax_in.pcolormesh(
            X,
            Y,
            vals.T,
            # extent=EXTENT,
            vmin=vmin,
            cmap=colour_map,
            zorder=2
            )
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        divider = make_axes_locatable(ax_in)
        side_bar = divider.append_axes("right", size="5%", pad=0.05)
        cbar = plt.colorbar(plot, cax=side_bar)
        cbar.locator = ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in


import seaborn as sns
def plot_seaborn_kde(query_data: DataFrame, bins=64,
                fig_in=None, ax_in=None, vmin=None, vmax=None):
    if fig_in is None:
        fig_in = plt.gcf()
    if ax_in is None:
        ax_in = fig_in.add_subplot(111)

    #jet = plt.get_cmap('rainbow')
    colour_map = copy.copy(plt.get_cmap('rainbow'))
    colour_map.set_under('black', alpha=0.0)

    # Add map
    img = mpimg.imread(environment['MAP_PATH'])
    ax_in.imshow(img, extent=EXTENT, zorder=0)
    if not query_data.empty:
        plot = sns.kdeplot(
            data=query_data,
            # x=query_data['xBins'], y=query_data['yBins'],
            x=query_data['xBin'].astype(float), y=query_data['yBin'].astype(float),
            weights=query_data['xCoordinate'].astype(int),
            palette=colour_map,
            # extent=EXTENT,
            gridsize=64,
            cbar=True,
            ax=ax_in,
            levels=4,
            # thresh=1,
            fill=True
        )
        # Reposition colourbar
        # https://stackoverflow.com/questions/18195758/set-matplotlib-colorbar-size-to-match-graph
        # divider = make_axes_locatable(ax_in)
        # side_bar = divider.append_axes("right", size="5%", pad=0.05)
        # cbar = plt.colorbar(plot, cax=side_bar)
        # cbar.locator = ticker.MaxNLocator(integer=True)
        # cbar.update_ticks()
        # cbar.ax.tick_params(labelsize=14)

    ax_in.axis('off')

    return ax_in

binned_dire = bin_pos_data(pos_dire_df)
vmin, vmax = binned_dire['xCoordinate'].quantile(0.7), binned_dire['xCoordinate'].quantile(0.999)
# axis = plot_counts_hist2d(binned_dire,
#                    bins=64, fig_in=fig, ax_in=axes[0],
#                    vmin=vmin, vmax=vmax)
# axis = plot_counts_pcolormesh(binned_dire,
#                    bins=64, fig_in=fig, ax_in=axes[0])

binned_dire_limited = bin_pos_data(pos_dire_limited_df)
vmin, vmax = binned_dire_limited['xCoordinate'].quantile(0.7), binned_dire_limited['xCoordinate'].quantile(0.999)
# axis = plot_counts_hist2d(binned_dire_limited,
#                    bins=64, fig_in=fig, ax_in=axes[1],
#                    vmin=vmin, vmax=vmax)
# axis = plot_counts_pcolormesh(binned_dire_limited,
#                    bins=64, fig_in=fig, ax_in=axes[1])
# axis.set_title('Latest 5 games')

# fig.tight_layout()
# fig.savefig("timado_pos_cached.png", bbox_inches='tight')

# plot_counts_pcolormesh(pos_dire_df, fig_in=fig, ax_in=axes[0], vmin=vmin)
# plot_counts_pcolormesh(pos_dire_limited_df, fig_in=fig, ax_in=axes[1], vmin=vmin)
axes[1].set_title('Latest 5 games')

# fig.tight_layout()
# fig.savefig("timado_pos_pmesh.png", bbox_inches='tight')

vals, xedge, yedge = get_binned_positioning(
    session, r_query,
    team, team.players[0], Team.DIRE,
    start, end,
    cache_id="test.json")