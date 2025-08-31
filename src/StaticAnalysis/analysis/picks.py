from herotools.HeroTools import convertName, HeroIDType, HeroIconPrefix
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image
from scipy.stats import binomtest
from pathlib import Path
from pandas import DataFrame
from sqlalchemy.orm import Query
from StaticAnalysis.lib.team_info import TeamInfo
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def make_image_annotation_flex(icon: Path, axes, x, y, size=1.0):
    icon = Image.open(icon)
    icon = icon.convert("RGBA")
    if size != 1.0:
        width, height = icon.size
        width = width*size
        height = height*size
        icon.thumbnail((width, height))

    imagebox = OffsetImage(icon)
    imagebox.image.axes = axes

    ab = AnnotationBbox(imagebox, (x, y),
                        xycoords='data',
                        boxcoords="data",
                        pad=0,
                        frameon=False,
                        box_alignment=(1.15, 0.5)
                        )

    axes.add_artist(ab)

    return imagebox


def plot_winpick_rate(table: DataFrame, axes,
                      pick_col: str = "picks", index_col: str = "heroName",
                      icon_col: str = "icon", winrate_col: str = "winrate",
                      prob_sort: str = "pgreater",
                      nHeroes=10, min_picks=0):
    icon_size = 0.8
    table = table.set_index(index_col)

    table = table.sort_values(by=[prob_sort, pick_col], ascending=True)
    ax = table[winrate_col].tail(nHeroes).plot.barh(ax=axes[1], width=-0.1, align='edge', ylabel="")
    offset = table[winrate_col].max() / 40
    axes[1].set_ylim(-0.1, len(table.tail(nHeroes)))
    for y, (_, t) in enumerate(table.tail(nHeroes).iterrows()):
        coords = (offset, y + 0.1)
        label = f"{int(t[pick_col])} picks - lossrate {int(round(t[winrate_col], 2)*100)}%"
        axes[1].annotate(label, coords, ha='left', va='baseline')
        # Icons
        icon = HeroIconPrefix / t[icon_col]
        make_image_annotation_flex(icon, axes[1], 0, y, icon_size)
    axes[1].set_title(f"Loss Rate Vs (Confidence >50% sorted)")

    table = table.loc[table[pick_col] >= min_picks]
    if table.empty:
        axes[0].text(0.5, 0.5, "No Data", fontsize=14,
                    horizontalalignment='center',
                    verticalalignment='center')
        axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        table = table.sort_values(by=[winrate_col, pick_col])
        ax = table[winrate_col].tail(nHeroes).plot.barh(xlim=(0, 1.1), ax=axes[0], width=-0.1, align='edge', ylabel="")
        axes[0].set_ylim(-0.1, len(table.tail(nHeroes)))
        for y, (_, t) in enumerate(table.tail(nHeroes).iterrows()):
            coords = (1.1/40, y + 0.1)
            label = f"{int(t[pick_col])} picks - lossrate {int(round(t[winrate_col], 2)*100)}%"
            axes[0].annotate(label, coords, ha='left', va='baseline')
            # Icons
            icon = HeroIconPrefix / t[icon_col]
            make_image_annotation_flex(icon, axes[0], 0, y, icon_size)
        axes[0].set_title(f"Loss Rate Vs (min {min_picks})")

    # Remove the old ylabels
    axes[0].set_yticklabels([])
    axes[1].set_yticklabels([])


def do_loss_opp_picks(r_query: Query, main_team: TeamInfo) -> Figure:
    """
    Build a plot for heroes the team loses most against.
    """
    df = DataFrame( [
        {'hero':p.hero, 'is_win':int(r.winner != r.get_side(main_team))}
        for r in r_query
        for t in r.teams if t.team != r.get_side(main_team)
        for p in t.draft if p.is_pick
    ])
    if df.empty:
        return None
    df['count'] = 1
    df = df.groupby('hero').sum().reset_index()
    df['icon'] = df['hero'].apply(lambda x: convertName(x, HeroIDType.NPC_NAME, HeroIDType.ICON_FILENAME))
    df['winrate'] = df['is_win']/df['count']
    # Get the agreement probability
    binom_row = lambda x: binomtest(x['is_win'], x['count'], 0.5, 'greater').pvalue
    df['pgreater'] = 1 - df.apply(binom_row, axis=1)
    
    fig = plt.figure(constrained_layout=True)
    ax1 = fig.subplots(ncols=2)
    fig.set_size_inches(10, 5)

    plot_winpick_rate(
        df, ax1,
        pick_col="count", index_col="hero",
        winrate_col="winrate", min_picks=3)

    return fig