import matplotlib.pyplot as plt
from herotools.HeroTools import (HeroIconPrefix, HeroIDType, convertName,
                                 heroShortName)
from pandas import DataFrame

from StaticAnalysis.analysis.visualisation import make_image_annotation_flex, x_label_icon
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.TeamSelections import PickBans
from matplotlib.ticker import MaxNLocator

BAD_REPLAY_SENTINEL = object()


def replay_prio_pick(replay: Replay, team: TeamInfo) -> DataFrame:
    first_pick_pattern = [[8,], [14, 15], [18], [23,]]
    second_pick_pattern = [[9,], [13,], [16, 17], [24,]]
    titles = ["P1", "P2", "P3", "P4"]
    columns = [f"{x} {y}" for x in titles for y in ['Available', 'Picked']]
    df = DataFrame(0, index=heroShortName.keys(), columns=columns)

    pattern = first_pick_pattern if replay.is_first_pick(team) else second_pick_pattern
    team_side = replay.get_side(team)
    opp_side = Team.DIRE if team_side == Team.RADIANT else Team.RADIANT

    picks = replay.get_team_dict()
    team_pb = picks[team_side]
    opp_pb = picks[opp_side]

    for pat, t in zip(pattern, titles):
        found = []
        hero_bag = set(heroShortName.keys())
        # Remove all heroes that appear before our pick
        p = pat[0]

        # Remove teams picks and bans, add picks
        pb: PickBans
        for pb in team_pb.draft:
            if pb.order < p:
                hero_bag.remove(pb.hero)
            elif pb.order in pat:
                if not pb.is_pick:
                    print(f"Invalid pickban pattern for {replay.replayID} at {pb.order}")
                found.append(pb.order)
                df.loc[pb.hero, f"{t} Picked"] += 1
        # Remove oppositions picks and bans
        for pb in opp_pb.draft:
            if pb.order > p:
                break
            hero_bag.remove(pb.hero)

        # Increment all heroes that were available (this includes those picked!)
        for h in hero_bag:
            df.loc[h, f"{t} Available"] += 1

        if len(found) != len(pat):
            print(f"Invalid pickban pattern for {replay.replayID}")
            print(f"found: {found} vs wanted: {pat}")
            return BAD_REPLAY_SENTINEL

    return df


NO_PICKS_SENTINEL = object()


def priority_pick_df(r_query, team, first_pick=False, second_pick=False):
    dfs = []
    r: Replay
    for r in r_query:
        # Skip if its first pick and were not collecting first!
        if r.is_first_pick(team) and not first_pick:
            continue
        # Skip if its second pick and were not collecting second!
        elif not r.is_first_pick(team) and not second_pick:
            continue
        df = replay_prio_pick(r, team)
        if df is BAD_REPLAY_SENTINEL:
            continue
        dfs.append(df)
    if dfs:
        for df in dfs[1:]:
            dfs[0] = dfs[0].add(df)

    titles = ["P1", "P2", "P3", "P4"]
    if dfs:
        for t in titles:
            dfs[0][f"{t} Percent"] = dfs[0][f"{t} Picked"]/dfs[0][f"{t} Available"]*100

        def conv_2(x): return convertName(x, HeroIDType.NPC_NAME, HeroIDType.ICON_FILENAME)
        dfs[0]['icon'] = dfs[0].index
        dfs[0]['icon'] = dfs[0]['icon'].apply(conv_2)

        return dfs[0]

    return NO_PICKS_SENTINEL


def plot_priority(table: DataFrame, ax_in,
                  col: str,
                  icon_col: str = "icon",
                  count_col=False,
                  nHeroes=10, horizontal=True):
    percent_col, picked_col, available_col = f"{col} Percent", f"{col} Picked", f"{col} Available"
    icon_size = 0.6
    table = table.loc[table[percent_col] > 0]
    max_val = max(table[percent_col].max(), 40)
    max_val += 10
    if horizontal:
        table = table.sort_values(by=[percent_col, available_col])
        table[percent_col].tail(nHeroes).plot.barh(xlim=(0, max_val), ax=ax_in, width=-0.1, align='edge', ylabel="")
        ax_in.set_ylim(-0.1, len(table.tail(nHeroes)))
        if count_col:
            ax_count = ax_in.twinx()
    else:
        table = table.sort_values(by=[percent_col, available_col], ascending=False)
        table[percent_col].head(nHeroes).plot.bar(ylim=(0, max_val), ax=ax_in, width=-0.2, align='edge', xlabel="")
        ax_in.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax_in.set_xlim(-0.5, len(table.tail(nHeroes)))
        if count_col:
            ax_count = ax_in.twinx()
            table[available_col].head(nHeroes).plot.bar(ylim=(0, max_val),ax=ax_count, width=0.2, align='edge', xlabel='', color='#ff7f00')
            ax_count.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax_count.tick_params(axis="y",direction="in")

    if horizontal:
        for y, (_, t) in enumerate(table.tail(nHeroes).iterrows()):

            coords = (1, y + 0.1)
            label = f"picked {int(t[picked_col])} "\
                    + f"from {int(t[available_col])}, "\
                    + f"{int(round(t[percent_col], 2))}%"

            ax_in.annotate(label, coords, ha='left', va='baseline')
            # Icons
            icon = HeroIconPrefix / t[icon_col]
            make_image_annotation_flex(icon, ax_in, 0, y, icon_size)

    if not horizontal:
        if not count_col:
            for y, (_, t) in enumerate(table.head(nHeroes).iterrows()):
                coords = (y + 0.1, max_val/10)
                label = f"{int(t[picked_col])} / "\
                        + f"{int(t[available_col])}, "\
                        + f"{int(round(t[percent_col], 2))}%"
                # label = f"{int(round(t[percent_col], 2))}%, "\
                #         + f"({int(t[picked_col])} / "\
                #         + f"{int(t[available_col])})"
                ax_in.annotate(label, coords, ha='left', va='baseline', rotation=90, fontsize=8)
        x_label_icon(ax_in, y_pos=-0.1, size=icon_size)
        # Labels

    # Remove the old ylabels
    if horizontal:
        ax_in.set_yticklabels([])
    else:
        ax_in.set_xticklabels([])

    return ax_in


def priority_picks(team, r_query, fig: plt.Figure, nHeroes=20,
                   first_pick=False, second_pick=False):
    titles_first = [
        "Pick 8",
        "Pick 14 and 15",
        "Pick 18",
        "Pick 23"
    ]
    titles_second = [
        "Pick 9",
        "Pick 13",
        "Pick 16 and 17",
        "Pick 24"
    ]
    if first_pick:
        titles = titles_first
    if second_pick:
        titles = titles_second
    full_df = priority_pick_df(r_query, team, first_pick=first_pick, second_pick=second_pick)

    y_inch = 2*6*2
    fig.set_size_inches(y_inch, 8)
    axes = fig.subplots(1, 4)
    # Handle no picks
    if full_df is NO_PICKS_SENTINEL:
        for a in axes:
            a.text(0.5, 0.5, "No Data", fontsize=14,
                   horizontalalignment='center',
                   verticalalignment='center')
        if first_pick:
            axes[0].set_ylabel("First pick", fontsize=20)
        if second_pick:
            axes[0].set_ylabel("Second pick", fontsize=20)
        return fig

    plot_priority(full_df, axes[0], "P1", nHeroes=nHeroes, count_col=False)
    axes[0].set_title(titles[0])
    plot_priority(full_df, axes[1], "P2", nHeroes=nHeroes, count_col=False)
    axes[1].set_title(titles[1])
    plot_priority(full_df, axes[2], "P3", nHeroes=nHeroes, count_col=False)
    axes[2].set_title(titles[2])
    plot_priority(full_df, axes[3], "P4", nHeroes=nHeroes, count_col=False)
    axes[3].set_title(titles[3])

    if first_pick:
        axes[0].set_ylabel("First pick", fontsize=20)
    if second_pick:
        axes[0].set_ylabel("Second pick", fontsize=20)

    axes[0].yaxis.set_label_coords(-0.15, 0.5)

    return fig


def priority_picks_double(team, r_query, fig: plt.Figure, nHeroes=20):
    titles_first = [
        "Pick 8",
        "Pick 14 and 15",
        "Pick 18",
        "Pick 23"
    ]
    titles_second = [
        "Pick 9",
        "Pick 13",
        "Pick 16 and 17",
        "Pick 24"
    ]
    first_df = priority_pick_df(r_query, team, first_pick=True, second_pick=False)
    second_df = priority_pick_df(r_query, team, first_pick=False, second_pick=True)

    x_inch = 8*2
    y_inch = x_inch * 1.414
    fig.set_size_inches(x_inch, y_inch)
    fig.set_size_inches(8.27, 11.69)
    axes_all = fig.subplots(4, 2)
    axes_first = [a[0] for a in axes_all]
    axes_second = [a[1] for a in axes_all]

    def _plot_pick(df: DataFrame, axes, titles):
        # Handle no picks
        if df is NO_PICKS_SENTINEL:
            for a in axes:
                a.text(0.5, 0.5, "No Data", fontsize=14,
                       horizontalalignment='center',
                       verticalalignment='center')

            return

        plot_priority(df, axes[0], "P1", nHeroes=nHeroes, horizontal=False)
        axes[0].set_ylabel(titles[0])
        # axes[0].yaxis.set_label_coords(-0.15, 0.5)
        plot_priority(df, axes[1], "P2", nHeroes=nHeroes, horizontal=False)
        axes[1].set_ylabel(titles[1])
        # axes[1].yaxis.set_label_coords(-0.15, 0.5)
        plot_priority(df, axes[2], "P3", nHeroes=nHeroes, horizontal=False)
        axes[2].set_ylabel(titles[2])
        # axes[2].yaxis.set_label_coords(-0.15, 0.5)
        plot_priority(df, axes[3], "P4", nHeroes=nHeroes, horizontal=False)
        axes[3].set_ylabel(titles[3])
        # axes[3].yaxis.set_label_coords(-0.15, 0.5)

    _plot_pick(first_df, axes_first, titles_first)
    _plot_pick(second_df, axes_second, titles_second)

    # Pick titles
    axes_all[0][0].set_title("First pick", fontsize=20)
    axes_all[0][1].set_title("Second pick", fontsize=20)
    for a in axes_second:
        a.yaxis.set_label_position("right")
        a.yaxis.tick_right()


    # axes_all[0][0].yaxis.set_label_coords(-0.15, 0.5)
    # axes_all[1][0].yaxis.set_label_coords(-0.15, 0.5)

    return fig
