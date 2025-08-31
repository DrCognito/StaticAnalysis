from StaticAnalysis.vis.summary import hero_win_rate_plot
from StaticAnalysis.analysis.Replay import (
    draft_summary, pair_rate, hero_win_rate, get_rune_control
    )
from StaticAnalysis.snippets.minimal_db import session, team_session, get_team
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.analysis.picks import make_image_annotation_flex
from herotools.important_times import MAIN_TIME
from matplotlib.ticker import MaxNLocator
from pandas import DataFrame


falcons = get_team(9247354)
spirit = get_team(7119388)
r_filter = Replay.endTimeUTC >= MAIN_TIME

r_query = falcons.get_replays(session).filter(r_filter)
team = falcons
limit = 20

from functools import partial
from herotools.HeroTools import HeroIDType, convertName, FullNameMap, HeroIconPrefix
df = hero_win_rate(r_query, team, limit=limit)
df = df.reset_index()
df['full_name'] = df['index'].map(FullNameMap)
# Add icon
iconographer = partial(
    convertName, input_format = HeroIDType.NPC_NAME, output_format = HeroIDType.ICON_FILENAME)
df['icon'] = df['index'].apply(iconographer)


from matplotlib.axes import Axes
from typing import List
def plot_winpick_rate(table: DataFrame, axes: List[Axes],
                      pick_col: str = "picks", index_col: str = "heroName",
                      icon_col: str = "icon", winrate_col: str = "winrate",
                      nHeroes=10, min_picks=0):
    icon_size = 0.5
    if table.empty:
        for a in axes:
            a.text(0.5, 0.5, "No Data", fontsize=14,
                        horizontalalignment='center',
                        verticalalignment='center')
            a.yaxis.set_major_locator(MaxNLocator(integer=True))
            
            return axes
    # Table setup
    table = table.set_index(index_col)
    table = table.sort_values(by=[pick_col, winrate_col, index_col], ascending=True)
    if nHeroes is not None:
        table = table.tail(nHeroes)
    ax = table[pick_col].plot.barh(ax=axes[0], width=-0.2, align='edge', ylabel="")
    axes[0].set_ylim(-0.2, len(table))
    for y, (_, t) in enumerate(table.iterrows()):
        coords = (0, y)
        label = f" {t[pick_col]}"
        axes[0].annotate(label, coords, ha='left', va='bottom')
        # Icons
        icon = HeroIconPrefix / t[icon_col]
        make_image_annotation_flex(icon, axes[0], 0, y, icon_size)
    axes[0].set_title(f"Picks")

    table = table.loc[table[pick_col] >= min_picks]

    # Seperate sort?
    # table = table.sort_values(by=[pick_col, winrate_col, index_col])
    ax = table[winrate_col].plot.barh(xlim=(0, 1.1), ax=axes[1], width=-0.2, align='edge', ylabel="")
    # axes[1].set_ylim(-0.1, len(table))
    for y, (_, t) in enumerate(table.iterrows()):
        coords = (0, y)
        label = f" {t[winrate_col]*100:.0f}%"
        axes[1].annotate(label, coords, ha='left', va='bottom')
        # Icons
        icon = HeroIconPrefix / t[icon_col]
        make_image_annotation_flex(icon, axes[0], 0, y, icon_size)
    
    axes[0].yaxis.set_tick_params(pad=15.0)
    axes[0].set_yticks(axes[0].get_yticks(), axes[0].get_yticklabels(), va='bottom')
    for a in axes[1:]:
        a.sharey(axes[0])
        a.get_yaxis().set_visible(False)

    axes[1].set_title(f"Win Rate")

    # Remove the old ylabels
    # axes[0].set_yticklabels([])
    # axes[1].set_yticklabels([])

import matplotlib.pyplot as plt
fig = plt.figure(constrained_layout=True)
axe = fig.subplots(ncols=2)
y_size = len(df) / 2.6
fig.set_size_inches(6, max(y_size, 6))


# fig.tight_layout()
plot_winpick_rate(
    table=df, axes=axe, pick_col="Total", index_col="full_name", winrate_col="Rate", nHeroes=None, min_picks=0
)
# fig.get_layout_engine().set(w_pad=0, wspace=0, hspace=0, h_pad=0)
fig.savefig("winrate_test.png")