import StaticAnalysis
from StaticAnalysis.lib.Common import ChainedAssignment
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.analysis.Player import player_heroes
from StaticAnalysis.analysis.Replay import (
    draft_summary, pair_rate, hero_win_rate, get_rune_control
    )
from StaticAnalysis.analysis.table_picks_panda import create_tables
from StaticAnalysis.analysis.visualisation import (
    plot_draft_summary, plot_flex_picks, plot_pick_pairs, plot_pick_context, plot_hero_winrates, 
    plot_runes
    )

from herotools.HeroTools import FullNameMap

from pathlib import Path
import matplotlib.pyplot as plt
from sqlalchemy.orm import Query, Session
from pandas import DataFrame
import concurrent.futures


PLOT_BASE_PATH = StaticAnalysis.CONFIG['output']['PLOT_OUTPUT']

def draft_summary_plot(draft_summary_df, output: str):
    fig = plt.figure(constrained_layout=True)
    fig, extra = plot_draft_summary(*draft_summary_df, fig)
    # fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
    # fig.subplots_adjust(wspace=0.1, hspace=0.25)
    # fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight')
    fig.savefig(output)
    fig.clf()
    return


def pick_context(team: TeamInfo, r_query: Query, limit, draft_summary_df, output: str):
    fig = plt.figure(constrained_layout=True)
    # fig.tight_layout(h_pad=3.0)
    fig, _, extra = plot_pick_context(draft_summary_df[0], team, r_query, fig, limit=limit)
    # fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=100)
    fig.savefig(output)
    fig.clf()
    return


def hero_flex(
    team: TeamInfo, r_query: Query, output: str, r_filter, limit=None):
    def _is_flex(*args):
        pass_count = 0
        for p in args:
            if p >= 1:
                pass_count += 1
        return pass_count
    flex_picks = player_heroes(
        StaticAnalysis.session, team, r_filt=r_filter, limit=limit, nHeroes=200)
    flex_picks['Counts'] = flex_picks.apply(lambda x: _is_flex(*x), axis=1)
    flex_picks = flex_picks.query('Counts > 1')
    with ChainedAssignment():
        flex_picks['std'] = flex_picks.iloc[:, 0:-1].std(axis=1)
        flex_picks['Name'] = flex_picks.index.map(FullNameMap)
    flex_picks = flex_picks.sort_values(['Name'], ascending=False)
    fig = plt.figure(constrained_layout=True)
    fig, extra = plot_flex_picks(flex_picks.iloc[:, 0:-3], fig)
    # fig.savefig(output, bbox_extra_artists=extra,
    #             bbox_inches='tight', dpi=150)
    fig.savefig(output)
    fig.clf()
    return


def pick_pairs(
    team: TeamInfo, r_query: Query, output: str, limit=None
    ):
    pick_pair_df = pair_rate(StaticAnalysis.session, r_query, team, limit=limit)
    if pick_pair_df:
        fig = plt.figure(constrained_layout=True)
        fig, extra = plot_pick_pairs(pick_pair_df, fig)
        # fig.tight_layout(h_pad=1.5)
        # fig.savefig(output, bbox_extra_artists=extra, bbox_inches='tight', dpi=400)
        fig.savefig(output)
        fig.clf()

    return


def hero_win_rate_plot(
    team: TeamInfo, r_query: Query, output: str, limit=None
    ):
    fig = plt.figure(constrained_layout=True)
    hero_win_rate_df = hero_win_rate(r_query, team, limit=limit)
    fig, _ = plot_hero_winrates(hero_win_rate_df, fig)
    # fig.savefig(output, bbox_inches='tight', dpi=300)
    fig.savefig(output)
    fig.clf()

    return


def rune_control(
    team: TeamInfo, rune_df: DataFrame, output: str
    ):
    fig = plt.figure(constrained_layout=True)
    fig, _ = plot_runes(rune_df, team, fig)
    # fig.tight_layout()
    # fig.subplots_adjust(hspace=0.35)
    # fig.savefig(output, bbox_inches='tight', dpi=200)
    fig.savefig(output)
    fig.clf()
    return


def pick_tables(
    team: TeamInfo, r_query: Query, output: str
    ):
    table_image = create_tables(r_query, team)
    table_image.save(output)
    
    return


def do_summary(team: TeamInfo, r_query, metadata: dict, r_filter, limit=None, postfix=''):
    '''Plots draft summary, player picks, pick pairs and hero win rates
       for the replays in r_query.'''
    team_path = Path(PLOT_BASE_PATH) / team.name / metadata['name']
    team_path.mkdir(parents=True, exist_ok=True)

    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
        draft_summary_df = draft_summary(StaticAnalysis.session, r_query, team, limit=limit)

        output = team_path / f'draft_summary{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_draft_summary{postfix}'] = relpath
        executor.submit(draft_summary_plot, draft_summary_df, output)

        if not draft_summary_df[0].empty:
            output = team_path / f'pick_context{postfix}.png'
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata[f'plot_pick_context{postfix}'] = relpath
            executor.submit(pick_context, team, r_query, limit, draft_summary_df, output)

        output = team_path / f'hero_flex{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_hero_flex{postfix}'] = relpath
        executor.submit(hero_flex, team, r_query, output, r_filter, limit)

        output = team_path / f'pick_pairs{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_pair_picks{postfix}'] = relpath
        executor.submit(pick_pairs, team, r_query, output, limit)

        output = team_path / f'hero_win_rate{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_win_rate{postfix}'] = relpath
        executor.submit(hero_win_rate_plot, team, r_query, output, limit)

        rune_df = get_rune_control(r_query, team, limit=limit)
        # One line
        one_line = len(rune_df) == 1
        # All that line is 0
        zeroed = all((rune_df.iloc[0] == [0, 0, 0, 0, 0, 0, 0, 0]).to_list())
        if not one_line and not zeroed:
            output = team_path / f'rune_control{postfix}.png'
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata[f'plot_rune_control{postfix}'] = relpath
            executor.submit(rune_control, team, rune_df, output)

        if limit is None:
            output = team_path / "pick_tables.png"
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata['plot_picktables'] = relpath
            executor.submit(pick_tables, team, r_query, output)
    
    return metadata