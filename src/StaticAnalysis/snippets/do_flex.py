from herotools.important_times import MAIN_TIME
from propubs.libs.vis import get_team_df
from propubs.libs.vis import process_dataframe_timeplit
from propubs.libs import TIME_LABELS
from StaticAnalysis.analysis.Player import player_heroes
from StaticAnalysis import session, team_session, pub_session
from StaticAnalysis.lib.Common import ChainedAssignment
from StaticAnalysis.analysis.visualisation import plot_flex_picks
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.vis.flex_vis import plot_flexstack_pub, fix_pubs_df_index


from sqlalchemy.orm import Query
from sqlalchemy import and_, or_
import matplotlib.pyplot as plt
from herotools.HeroTools import FullNameMap


r_filter = Replay.endTimeUTC >= MAIN_TIME
def get_team(name) -> TeamInfo:
    t_filter = or_(TeamInfo.team_id == name, TeamInfo.name == name)
    team = team_session.query(TeamInfo).filter(t_filter).one_or_none()

    return team
tundra  = get_team(8291895)
team = tundra
fig = plt.figure()
# fig1, fig2 = fig.subfigures(1,2)


# Normal flex plot
def _is_flex(*args):
        pass_count = 0
        for p in args:
            if p >= 1:
                pass_count += 1
        return pass_count
flex_picks = player_heroes(session, team, r_filt=r_filter, nHeroes=200)
flex_picks['Counts'] = flex_picks.apply(lambda x: _is_flex(*x), axis=1)
flex_picks = flex_picks.query('Counts > 1')
with ChainedAssignment():
    flex_picks['std'] = flex_picks.iloc[:, 0:-1].std(axis=1)
flex_picks['Name'] = flex_picks.index.map(FullNameMap)
# flex_picks = flex_picks.sort_values(['Counts', 'std'], ascending=True)
flex_picks = flex_picks.sort_values(['Name'], ascending=False)
fig, extra = plot_flex_picks(flex_picks.iloc[:, 0:-3], fig)
output = 'flex_test.png'
# fig.savefig(output, bbox_extra_artists=extra,
#             bbox_inches='tight', dpi=150)
# fig.clf()

fig2 = plt.figure()

# Pub flex plot
min_time = MAIN_TIME
flex_pubs_df = get_team_df(team, pub_session, min_time,
    post_process=process_dataframe_timeplit, maxtime=None)
# Fix me chain with post_process?
flex_pubs_df = fix_pubs_df_index(flex_pubs_df)

output = f'flex_pubs_test.png'
fig = plot_flexstack_pub(flex_pubs_df, contexts=TIME_LABELS, fig=fig2)
# fig.savefig(output, bbox_inches='tight', dpi=150)
# fig.clf()

# plt.show()