from StaticAnalysis.tests.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.TeamSelections import PickBans
from StaticAnalysis.analysis.route_vis import plot_pregame_players
from StaticAnalysis.analysis.visualisation import make_image_annotation_flex
import matplotlib.pyplot as plt
from sqlalchemy import and_, or_
from herotools.important_times import ImportantTimes, nice_time_names
from herotools.HeroTools import heroShortName, convertName, HeroIDType, HeroIconPrefix
from pandas import DataFrame


def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team


r_filter = Replay.endTimeUTC >= ImportantTimes['Patch_7_33']
proc_team = 8255756  # Evil Geniuses
opp = 8599101 # Gaimin Gladiators
liquid = 2163
team = get_team(liquid)
opp_team = get_team(opp)
r_query = team.get_replays(session).filter(r_filter)

BAD_REPLAY_SENTINEL = object()


def replay_prio_pick(replay: Replay, team: TeamInfo) -> DataFrame:
    first_pick_pattern = [[5,], [8,], [16, 17], [23,]]
    second_pick_pattern = [[6, 7], [15,], [18,], [24,]]
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


def priority_pick_df(r_query, team):
    dfs = []
    for r in r_query:
        df = replay_prio_pick(r, team)
        if df is BAD_REPLAY_SENTINEL:
            continue
        dfs.append(df)
    if dfs:
        for df in dfs[1:]:
            dfs[0] = dfs[0].add(df)

    titles = ["P1", "P2", "P3", "P4"]
    for t in titles:
        dfs[0][f"{t} Percent"] = dfs[0][f"{t} Picked"]/dfs[0][f"{t} Available"]*100

    def conv_2(x): return convertName(x, HeroIDType.NPC_NAME, HeroIDType.ICON_FILENAME)
    dfs[0]['icon'] = dfs[0].index
    dfs[0]['icon'] = dfs[0]['icon'].apply(conv_2)

    return dfs[0]


def plot_priority(table: DataFrame, ax_in,
                  percent_col: str,
                  icon_col: str = "icon",
                  nHeroes=10):
    icon_size = 0.8
    table = table.loc[table[percent_col] > 0]
    table = table.sort_values(by=[percent_col,])
    max_val = max(table[percent_col].max(), 50)
    table[percent_col].tail(nHeroes).plot.barh(xlim=(0, max_val), ax=ax_in, width=-0.1, align='edge', ylabel="")
    ax_in.set_ylim(-0.1, len(table.tail(nHeroes)))
    for y, (_, t) in enumerate(table.tail(nHeroes).iterrows()):
        coords = (1, y + 0.1)
        label = f"{int(round(t[percent_col], 2))}%"
        ax_in.annotate(label, coords, ha='left', va='baseline')
        # Icons
        icon = HeroIconPrefix / t[icon_col]
        make_image_annotation_flex(icon, ax_in, 0, y, icon_size)

    # Remove the old ylabels
    ax_in.set_yticklabels([])

    return ax_in


def do_priority_picks(r_query, team, fig: plt.Figure, nHeroes=20):
    full_df = priority_pick_df(r_query, team)
    y_inch = 2*6*(nHeroes/10)
    fig.set_size_inches(15, y_inch)
    axes = fig.subplots(2,2)
    plot_priority(full_df, axes[0][0], "P1 Percent", nHeroes=nHeroes)
    axes[0][0].set_title("Pick 5 (first) or Picks 6 and 7")
    plot_priority(full_df, axes[0][1], "P2 Percent", nHeroes=nHeroes)
    axes[0][1].set_title("Pick 15 or Picks 16 and 17 (first)")
    plot_priority(full_df, axes[1][0], "P3 Percent", nHeroes=nHeroes)
    axes[1][0].set_title("Pick 23")
    plot_priority(full_df, axes[1][1], "P4 Percent", nHeroes=nHeroes)
    axes[1][1].set_title("Pick 24")

    return fig



fig = plt.figure()
# nHeroes = 10
# y_inch = 6*(nHeroes/10)
# fig.set_size_inches(7.5, y_inch)
# ax = fig.subplots(1)
# plot_priority(full_df, ax, percent_col="P1 Percent", nHeroes=nHeroes)
# ax.set_title("Pick 5 (first) or Picks 6 and 7")

fig = do_priority_picks(r_query, team, fig, nHeroes=20)
fig.savefig("prio_test.png", bbox_inches="tight")