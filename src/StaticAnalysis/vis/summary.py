import StaticAnalysis
from StaticAnalysis import LOG
from StaticAnalysis.lib.Common import ChainedAssignment
from StaticAnalysis.lib.team_info import TeamInfo
from StaticAnalysis.analysis.Player import player_heroes
from StaticAnalysis.analysis.Replay import (
    draft_summary, pair_rate, hero_win_rate, get_rune_control
    )
from StaticAnalysis.analysis.table_picks_panda import create_tables
from StaticAnalysis.analysis.visualisation import (
    plot_draft_summary, plot_flex_picks, plot_pick_pairs, plot_pick_context, plot_hero_winrates, 
    plot_runes, plot_hero_lossrates
    )
from StaticAnalysis.analysis.picks import do_loss_opp_picks

from herotools.HeroTools import FullNameMap

from pathlib import Path
from matplotlib.figure import Figure
from PIL.Image import Image
import matplotlib.pyplot as plt
from sqlalchemy.orm import Query, Session
from pandas import DataFrame
import concurrent.futures


PLOT_BASE_PATH = StaticAnalysis.CONFIG['output']['PLOT_OUTPUT']

def _save_plot(fig: Figure, output: str):
    fig.savefig(output)
    fig.clf()

def draft_summary_plot(draft_summary_df) -> Figure:
    fig = plt.figure(constrained_layout=True)
    fig, _ = plot_draft_summary(*draft_summary_df, fig)

    return fig


def pick_context(team: TeamInfo, r_query: Query, limit, draft_summary_df):
    fig = plt.figure(constrained_layout=True)
    fig, _, _ = plot_pick_context(draft_summary_df[0], team, r_query, fig, limit=limit)

    return fig


def hero_flex(
    team: TeamInfo, r_filter, limit=None) -> Figure:
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
    fig, _ = plot_flex_picks(flex_picks.iloc[:, 0:-3], fig)

    return fig


def pick_pairs(
    team: TeamInfo, r_query: Query, limit=None
    ) -> Figure:
    pick_pair_df = pair_rate(StaticAnalysis.session, r_query, team, limit=limit)
    if pick_pair_df:
        fig = plt.figure(constrained_layout=True)
        fig, _ = plot_pick_pairs(pick_pair_df, fig)
        return fig

    return None


from functools import partial
from herotools.HeroTools import HeroIDType, convertName, FullNameMap, HeroIconPrefix
from StaticAnalysis.analysis.visualisation import plot_winpick_rate
def hero_win_rate_plot(team: TeamInfo, r_query: Query, limit=None):
    df = hero_win_rate(r_query, team, limit=limit)
    df = df.reset_index()
    df['full_name'] = df['index'].map(FullNameMap)
    # Add icon
    iconographer = partial(
        convertName, input_format = HeroIDType.NPC_NAME, output_format = HeroIDType.ICON_FILENAME)
    df['icon'] = df['index'].apply(iconographer)
    
    win = plt.figure(constrained_layout=True)
    axe = win.subplots(ncols=2)
    y_size = len(df) / 3.0
    win.set_size_inches(6, max(y_size, 6))


    # fig.tight_layout()
    plot_winpick_rate(
        table=df, axes=axe, pick_col="Total",
        index_col="full_name", winrate_col="Rate", nHeroes=None,
        min_picks=0
    )
    
    # win = plt.figure(constrained_layout=True)
    # win, _ = plot_hero_winrates(hero_win_rate_df, win)
    loss = plt.figure(constrained_layout=True)
    # Reset this to the old index
    df = df.set_index('index')
    loss, _ = plot_hero_lossrates(df, loss)

    return win, loss


def rune_control(team: TeamInfo, rune_df: DataFrame) -> Figure:
    fig = plt.figure(constrained_layout=True)
    fig, _ = plot_runes(rune_df, team, fig)
    return fig


def pick_tables(team: TeamInfo, r_query: Query) -> Image:
    return create_tables(r_query, team)


def log_future(future: concurrent.futures.Future):
    try:
        future.result()
    except Exception as esc:
        LOG.opt(exception=True).error("Thread failed")
    else:
        LOG.debug("Summary save plot thread finished.")

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
        fig = draft_summary_plot(draft_summary_df)
        fremtiden = executor.submit(_save_plot, fig, output)
        fremtiden.add_done_callback(log_future)
        
        if not draft_summary_df[0].empty:
            output = team_path / f'pick_context{postfix}.png'
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata[f'plot_pick_context{postfix}'] = relpath
            fig = pick_context(team, r_query, limit, draft_summary_df)
            fremtiden = executor.submit(_save_plot, fig, output)
            fremtiden.add_done_callback(log_future)

        output = team_path / f'hero_flex{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_hero_flex{postfix}'] = relpath
        fig = hero_flex(team, r_filter, limit)
        fremtiden = executor.submit(_save_plot, fig, output)
        fremtiden.add_done_callback(log_future)

        output = team_path / f'pick_pairs{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_pair_picks{postfix}'] = relpath
        fig = pick_pairs(team, r_query, limit)
        if fig is not None:
            fremtiden = executor.submit(_save_plot, fig, output)
            fremtiden.add_done_callback(log_future)

        output = team_path / f'hero_win_rate{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_win_rate{postfix}'] = relpath
        win, loss = hero_win_rate_plot(team, r_query, limit)
        fremtiden = executor.submit(_save_plot, win, output)
        fremtiden.add_done_callback(log_future)

        output = team_path / f'hero_loss_rate{postfix}.png'
        relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
        metadata[f'plot_loss_rate{postfix}'] = relpath
        fremtiden = executor.submit(_save_plot, loss, output)
        fremtiden.add_done_callback(log_future)

        rune_df = get_rune_control(r_query, team, limit=limit)
        # One line
        one_line = len(rune_df) == 1
        # All that line is 0
        zeroed = all((rune_df.iloc[0] == [0, 0, 0, 0, 0, 0, 0, 0]).to_list())
        if not one_line and not zeroed:
            output = team_path / f'rune_control{postfix}.png'
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata[f'plot_rune_control{postfix}'] = relpath
            fig = rune_control(team, rune_df)
            fremtiden = executor.submit(_save_plot, fig, output)
            fremtiden.add_done_callback(log_future)

        if limit is None:
            output = team_path / "pick_tables.png"
            relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
            metadata['plot_picktables'] = relpath
            table = pick_tables(team, r_query)
            table.save(output)
            
            fig = do_loss_opp_picks(
                r_query, team
            )
            if fig is None:
                metadata['lossvs_opp'] = None
            else:
                output = team_path / "lossvs_opp.png"
                relpath = str(output.relative_to(Path(PLOT_BASE_PATH)))
                metadata['lossvs_opp'] = relpath
                fremtiden = executor.submit(_save_plot, fig, output)
                fremtiden.add_done_callback(log_future)

    return metadata