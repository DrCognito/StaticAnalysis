from StaticAnalysis.analysis.Player import player_heroes
from StaticAnalysis.analysis.visualisation import plot_flex_picks
from StaticAnalysis.lib.Common import ChainedAssignment
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay
from sqlalchemy import and_, or_
from StaticAnalysis import session, team_session, pub_session

import matplotlib.pyplot as plt
from herotools.important_times import MAIN_TIME
from propubs.libs.vis import get_player_dataframe, process_dataframe, get_team_df, plot_propub, colour_list, plot_team_pubs, plot_team_pubs_timesplit, process_dataframe_timeplit
from pandas import DataFrame, concat, Series
from collections import Counter
from propubs.libs import TIME_LABELS
from StaticAnalysis.vis.flex_vis import plot_flexstack, combine_pub_comp
from herotools.lib.position import strict_pos, loose_pos, mixed_pos

xtreme_gaming = 8261500
heroic = 9303484
moodeng = 9678064
r_filter = Replay.endTimeUTC >= MAIN_TIME

def get_team(name):
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team
team = get_team(moodeng)

def _is_flex(*args):
        pass_count = 0
        for p in args:
            if p >= 1:
                pass_count += 1
        return pass_count

limit = None # Replay limit

flex_picks = player_heroes(session, team, r_filt=r_filter, limit=limit, nHeroes=200)
flex_picks['Counts'] = flex_picks.apply(lambda x: _is_flex(*x), axis=1)
flex_picks = flex_picks.query('Counts > 1')
with ChainedAssignment():
    flex_picks['std'] = flex_picks.iloc[:, 0:-1].std(axis=1)
flex_picks = flex_picks.sort_values(['Counts', 'std'], ascending=True)

postfix = ""
fig = plt.figure()
fig, extra = plot_flex_picks(flex_picks.iloc[:, 0:-2], fig)
output = f'hero_flex{postfix}.png'
fig.savefig(output, bbox_extra_artists=extra,
            bbox_inches='tight', dpi=150)

pubs_df = get_team_df(team, pub_session, MAIN_TIME)
pubs_df_time_none = get_team_df(team, pub_session, MAIN_TIME, post_process=process_dataframe_timeplit)
pubs_df_time_loose = get_team_df(
    team, pub_session, MAIN_TIME, post_process=process_dataframe_timeplit,
    pos_requirements=loose_pos
    )
pubs_df_time_strict = get_team_df(
    team, pub_session, MAIN_TIME, post_process=process_dataframe_timeplit,
    pos_requirements=strict_pos
    )


full_picks = player_heroes(session, team, r_filt=r_filter, limit=limit, nHeroes=200)
# polson_pubs = pubs_df_time_splot['poloson']
# # Fix the index to be more convenient
# polson_pubs.index = [i[1] for i in polson_pubs.index.to_flat_index()]

processed_none = combine_pub_comp(pubs_df_time_none, full_picks, default_cols=[TIME_LABELS])
processed_loose = combine_pub_comp(pubs_df_time_loose, full_picks, default_cols=[TIME_LABELS])
processed_strict = combine_pub_comp(pubs_df_time_strict, full_picks, default_cols=[TIME_LABELS])


def get_flex_heroes(team_df: dict):
    seen = set()
    flexes = set()

    df: DataFrame
    for _, df in team_df.items():
        for hero in df.index:
            if hero not in seen:
                seen.add(hero)
            else:
                flexes.add(hero)
                
    return flexes


def counter_flex_heroes(team_df: dict) -> Counter:
    df: DataFrame
    counts = Counter()
    for _, df in team_df.items():
        df = df.loc[~(df==0).all(axis=1)] # Ensure not everything is zero!
        counts.update(df.index)

    return counts

flexes = get_flex_heroes(processed_none)
counts = counter_flex_heroes(processed_none)

def get_flex_totals(team_df: dict) -> Series:
    # Combine our seperate player dfs
    totals = concat(processed_none).reset_index()
    # Group by level 1 which should be the hero name (npc_...) and count players
    counts = totals[['level_0', 'level_1']].groupby('level_1').count()
    # Check we have more than one for a flex pick
    counts = counts[counts['level_0'] > 1]
    # Using the remaining hero names that are flex picks, filter hero name
    totals = totals[totals['level_1'].isin(counts.index)].groupby('level_1').sum()
    # Time lables + comp to sum over
    labels = [*TIME_LABELS, 'comp']
    # Do the sum and sort
    totals['sum'] = totals[labels].sum(axis=1, numeric_only=True)
    totals = totals.sort_values("sum", ascending=False)
    
    # Return just the one column
    return totals['sum']

flex_count = get_flex_totals(processed_none)

fig = plt.figure()
labels = [*TIME_LABELS, 'comp']
fig = plot_flexstack(processed_none, labels, fig)
output = f'hero_flex_pub.png'
fig.savefig(output, bbox_inches='tight', dpi=150)

fig.clf()
fig = plot_flexstack(processed_loose, labels, fig)
output = f'hero_flex_pub_loose.png'
fig.savefig(output, bbox_inches='tight', dpi=150)

fig.clf()
fig = plot_flexstack(processed_strict, labels, fig)
output = f'hero_flex_pub_strict.png'
fig.savefig(output, bbox_inches='tight', dpi=150)