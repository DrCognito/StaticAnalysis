from pandas import DataFrame, Series, concat
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from herotools.HeroTools import (HeroIconPrefix, HeroIDType, convertName,
                                 heroShortName)
from matplotlib import colormaps as mpl_colormaps
from StaticAnalysis.analysis.visualisation import make_image_annotation_flex
from PIL import Image
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import matplotlib.patches as mpatches

colour_map = [
    mpl_colormaps.get('cool'),
    mpl_colormaps.get('summer'),
    mpl_colormaps.get('winter'),
    mpl_colormaps.get('spring'),
    mpl_colormaps.get('copper')
    ]
error_colourmap = mpl_colormaps.get('Reds')

def add_yticks(axe: Axes, new_locs: list, new_labels: list):
    '''
    Add the labels as the positions to the ticks from tick_func.
    Pyplot uses xtick() and ytick() function to let you retrieve current.
    This function retrieves and adds these new ones.
    '''
    locs = list(axe.get_yticks())
    locs += new_locs
    
    labels = list(axe.get_yticklabels())
    labels += new_labels
    axe.set_yticks(locs, labels)
    # axe.set_xticklabels(labels)

    return axe

def plot_hero_flexstack(
    offset: float, barh: float, bargap: float,
    colour_map: dict, colour_float: dict,
    plot_hatching: dict, plot_column: list,
    plot_labels: dict,
    hero_frequencies: dict, axe: Axes
    ) -> float:
    '''
    Plot the stack of played comp and pub games for a player for a single hero.
    Keyword arguments:
    offset -- the vertical offset in the plot to start plotting with
    barh -- the height of the bar
    bargap -- gap between each bar
    colour_map -- dict of 5 colours corresponding to player names
    colour_float -- dict for the intensity of the colourmaps for each column
    plot_hatching -- dict of plot styles corresponding to plot column
    plot_column -- list of column names to plot
    plot_labels -- dict of player: dict, dict: label for labeling any plot
    hero_frequencies -- dictionary of player:pick frequencies as a Series
    axe -- matplotlib Axes for plotting into
    '''
    start_offset = offset
    # Name and positions
    xticks = []
    xnames = []
    p: str
    s: Series
    for p, s in hero_frequencies.items():
        if s.empty:
            continue
        # left of the bar so we can stack them
        left = 0
        # itterate through context, plot our stacked bars
        for context in plot_column:
            # width = s.loc[context]
            width = s[context]
            if width == 0:
                continue
            # Should end up as None if p or context are missing
            label = plot_labels.get(p, {}).get(context, None)
            hatching = plot_hatching.get(context, None)
            cmap = colour_map.get(p, error_colourmap)
            colour = cmap(colour_float.get(context, 0))

            # Plot the main bar
            axe.barh(
                offset, width, height=barh, left=left,
                label=label, hatch=hatching, color=colour,
                zorder=0, edgecolor='white', linewidth=0
                )
            # Plot an outline seperately
            axe.barh(
                offset, width, height=barh, left=left,
                label=label, color='none',
                edgecolor = 'black', linewidth=1, zorder=1
                )
            axe.set_yticks([offset,], [p,])
            # Add the left offset
            left += width
        # Add name
        xticks.append(offset)
        xnames.append(p)
        # Move the offset past barh and bargap
        offset += barh + bargap

    return offset, xticks, xnames


def get_flex_totals(team_df: dict, labels: list, use_cols: list = None) -> Series:
    # Combine our seperate player dfs
    totals = concat(team_df).reset_index()
    if use_cols is not None:
        totals = totals.loc[:, ['level_0', 'level_1'] + use_cols]
        # Check if some are now zero with filtering.
        totals = totals.loc[~(totals[use_cols]==0).all(axis=1)]
    # Group by level 1 which should be the hero name (npc_...) and count players
    counts = totals[['level_0', 'level_1']].groupby('level_1').count()
    # Check we have more than one for a flex pick
    counts = counts[counts['level_0'] > 1]
    # Using the remaining hero names that are flex picks, filter hero name
    totals = totals[totals['level_1'].isin(counts.index)].groupby('level_1').sum()
    # Do the sum and sort
    if totals.empty:
        totals['sum'] = []
    else:
        totals['sum'] = totals[labels].sum(axis=1, numeric_only=True)
        totals = totals.sort_values("sum", ascending=False)
    
    # Return just the one column
    return totals['sum']


def get_flex_totals_pub(team_df: dict, labels: list, use_cols: list = None) -> Series:
    # Combine our seperate player dfs
    totals = concat(team_df).reset_index()
    if use_cols is not None:
        totals = totals.loc[:, ['level_0', 'hero_name'] + use_cols]
        # Check if some are now zero with filtering.
        totals = totals.loc[~(totals[use_cols]==0).all(axis=1)]
    # Group by level 1 which should be the hero name (npc_...) and count players
    counts = totals[['level_0', 'hero_name']].groupby('hero_name').count()
    # Check we have more than one for a flex pick
    counts = counts[counts['level_0'] > 1]
    # Using the remaining hero names that are flex picks, filter hero name
    totals = totals[totals['hero_name'].isin(counts.index)].groupby('hero_name').sum()
    # Do the sum and sort
    if totals.empty:
        totals['sum'] = []
    else:
        totals['sum'] = totals[labels].sum(axis=1, numeric_only=True)
        totals = totals.sort_values("sum", ascending=False)
    
    # Return just the one column
    return totals['sum']


def combine_pub_comp(pub_dfs: dict, comp_df: DataFrame, default_cols: list):
    output = {}
    for player in comp_df.columns:
        if pub_dfs[player].empty:
            output[player] = DataFrame(columns=default_cols)
        else:
            output[player] = pub_dfs[player].copy()
        output[player].index = [i[1] for i in output[player].index.to_flat_index()]
        output[player]['comp'] = comp_df[player]
        output[player] = output[player].fillna(0)
        output[player] = output[player].loc[~(output[player]==0).all(axis=1)]

    return output


def add_hero_icon(h: str, x, y, size, axe: Axes):
    try:
        # Get and resize the hero icon.
        icon = HeroIconPrefix / convertName(
            h, HeroIDType.NPC_NAME,
            HeroIDType.ICON_FILENAME
        )
    except (ValueError, KeyError):
        print("Unable to find hero icon for 2: " + h)
        raise KeyError
    
    icon = Image.open(icon)
    icon = icon.convert("RGBA")
    if size != 1.0:
        width, height = icon.size
        width = width*size
        height = height*size
        icon.thumbnail((width, height))

    imagebox = OffsetImage(icon)
    imagebox.image.axes = axe

    ab = AnnotationBbox(imagebox, (x, y),
                        xycoords='data',
                        boxcoords="data",
                        pad=0,
                        frameon=False,
                        box_alignment=(1.15, 0.5)
                        )

    axe.add_artist(ab)

    return imagebox


def plot_flexstack(combined_df: dict, contexts: list, fig: Figure, limit=20):
    plot_style = {
        'barh':1.0,
        'bargap':0.1,
        'colour_map':{p:c for p, c in zip(combined_df, colour_map)},
        'plot_hatching':{
            'comp': None,
            '<3 days':'/',
            '3 to 7 days':'x',
            '7 to 30 days':'o'},
        'colour_float':{
            'comp': 0,
            '<3 days':0.2,
            '3 to 7 days':0.4,
            '7 to 30 days':0.6},
        'plot_column':['comp', '<3 days', '3 to 7 days', '7 to 30 days'],
    }
    # A default label for making a legend from the comp thing
    plot_labels = {}
    for p in combined_df:
        plot_labels[p] = {}
        plot_labels[p]['comp'] = p

    flex_count = get_flex_totals(combined_df, contexts)

    # Figure setup
    # fig.set_size_inches(6, max(1.0*len(flex_count[20:]), 6))
    fig.set_size_inches(6, max(1.0*len(flex_count[20:]), 10))
    axe = fig.subplots()
    # Build a dictionary of rows for each hero
    # Limit controls the max number of heroes to plot
    offset = 0
    yticks = []
    ylabels = []
    for h in flex_count.index[:limit]:
        plot_dict = {}
        for p, df in combined_df.items():
            try:
                plot_dict[p] = df.loc[h]
            except KeyError:
                # print(f"No data for hero {h} player {p}")
                pass
        offset, ticks, labels = plot_hero_flexstack(
            offset=offset,
            plot_labels=plot_labels,
            hero_frequencies=plot_dict,
            axe=axe,
            **plot_style,
        )
        size = 0.6
        x_pos = 0.0
        y_pos = (ticks[0] + ticks[-1]) / 2.0
        # Add the hero ircon
        add_hero_icon(h, x_pos, y_pos, size, axe)
        offset += 3*plot_style['bargap']
        yticks += ticks
        ylabels += labels
        
    axe.set_yticks(yticks, ylabels)
    axe.yaxis.set_tick_params(pad=20)
    # Make legend manually
    # Player labels
    handles = []
    for p, cmap in plot_style['colour_map'].items():
        patch = mpatches.Patch(color=cmap(0), label=p)
        handles.append(patch)
    l1 = axe.legend(handles=handles)
    # Time labels
    time_cmap = mpl_colormaps.get('copper')
    handles_time = []
    for t, s in plot_style['plot_hatching'].items():
        patch = mpatches.Patch(facecolor=time_cmap(0), hatch=s, label=t, edgecolor='white')
        handles_time.append(patch)
    axe.add_artist(l1)
    axe.legend(
        handles = handles_time,
        ncol = 3,
        loc=(0.0, -0.08)
        )

    return fig


def fix_pubs_df_index(pubs_df: dict) -> dict:
    df: DataFrame
    for p, df in pubs_df.items():
        df.index = [i[1] for i in df.index]
        df = df.loc[~(df==0).all(axis=1)]
        pubs_df[p] = df

    return pubs_df


def plot_flexstack_pub(pubs_df: dict, contexts: list, fig: Figure, limit=20):
    plot_style = {
        'barh':1.0,
        'bargap':0.1,
        'colour_map':{p:c for p, c in zip(pubs_df, colour_map)},
        'plot_hatching':{
            '<3 days':'/',
            '3 to 7 days':'x',
            '7 to 30 days':'o'},
        'colour_float':{
            '<3 days':0.2,
            '3 to 7 days':0.4,
            '7 to 30 days':0.6},
        'plot_column':['<3 days', '3 to 7 days', '7 to 30 days'],
    }

    flex_count = get_flex_totals(pubs_df, contexts)

    # Figure setup
    # fig.set_size_inches(6, max(1.0*len(flex_count[20:]), 6))
    fig.set_size_inches(6, max(1.0*len(flex_count[20:]), 10))
    axe = fig.subplots()
    axe.set_title("Pubs")
    if flex_count.empty:
        axe.text(0.5, 0.5, "No Data", fontsize=14,
            horizontalalignment='center',
            verticalalignment='center'
        )
    # Build a dictionary of rows for each hero
    # Limit controls the max number of heroes to plot
    offset = 0
    yticks = []
    ylabels = []
    plot_labels = {}
    p_order = list(pubs_df.keys())[::-1]
    for h in flex_count.index[:limit]:
        plot_dict = {}
        for p in p_order:
            df = pubs_df[p]
            try:
                plot_dict[p] = df.loc[h]
            except KeyError:
                # print(f"No data for hero {h} player {p}")
                pass
        offset, ticks, labels = plot_hero_flexstack(
            offset=offset,
            plot_labels=plot_labels,
            hero_frequencies=plot_dict,
            axe=axe,
            **plot_style,
        )
        size = 0.6
        x_pos = 0.0
        y_pos = (ticks[0] + ticks[-1]) / 2.0
        # Add the hero ircon
        add_hero_icon(h, x_pos, y_pos, size, axe)
        offset += 3*plot_style['bargap']
        yticks += ticks
        ylabels += labels
        
    axe.set_yticks(yticks, ylabels)
    axe.yaxis.set_tick_params(pad=20)
    # Make legend manually
    # Player labels
    handles = []
    for p, cmap in plot_style['colour_map'].items():
        patch = mpatches.Patch(color=cmap(0), label=p)
        handles.append(patch)
    l1 = axe.legend(handles=handles)
    # l1_bbox = l1.get_bbox_to_anchor().inverse_transformed(axe.transAxes)
    l1_bbox = l1.get_bbox_to_anchor()
    l1_bbox = l1_bbox.transformed(fig.transFigure.inverted())
    # Time labels
    time_cmap = mpl_colormaps.get('copper')
    handles_time = []
    for t, s in plot_style['plot_hatching'].items():
        patch = mpatches.Patch(facecolor=time_cmap(0), hatch=s, label=t, edgecolor='white')
        handles_time.append(patch)
    axe.add_artist(l1)
    #Legend pos adjustments

    axe.legend(
        handles = handles_time,
        # bbox=l1_bbox,
        # loc='upper right', bbox_to_anchor=(l1_bbox.xmax, l1_bbox.ymin),
        loc='upper right', bbox_to_anchor=(l1_bbox.xmax, l1_bbox.ymax - 0.11),
        # loc=(0.05, 0.01),
        bbox_transform=fig.transFigure
        )
    axe.xaxis.get_major_locator().set_params(integer=True)

    return fig


def plot_flex_comp(pubs_df: dict, contexts: list, fig: Figure, limit=20):
    plot_style = {
        'barh':1.0,
        'bargap':0.1,
        'colour_map':{p:c for p, c in zip(pubs_df, colour_map)},
        'plot_hatching':{
            '<3 days':'/',
            '3 to 7 days':'x',
            '7 to 30 days':'o'},
        'colour_float':{
            '<3 days':0,
            '3 to 7 days':0.2,
            '7 to 30 days':0.4},
        'plot_column':['<3 days', '3 to 7 days', '7 to 30 days'],
    }

    flex_count = get_flex_totals(pubs_df, contexts)

    # Figure setup
    # fig.set_size_inches(6, max(1.0*len(flex_count[20:]), 6))
    fig.set_size_inches(6, max(1.0*len(flex_count[20:]), 10))
    axe = fig.subplots()
    # Build a dictionary of rows for each hero
    # Limit controls the max number of heroes to plot
    offset = 0
    yticks = []
    ylabels = []
    plot_labels = {}
    p_order = list(pubs_df.keys())[::-1]
    for h in flex_count.index[:limit]:
        plot_dict = {}
        for p in p_order:
            df = pubs_df[p]
            try:
                plot_dict[p] = df.loc[h]
            except KeyError:
                # print(f"No data for hero {h} player {p}")
                pass
        offset, ticks, labels = plot_hero_flexstack(
            offset=offset,
            plot_labels=plot_labels,
            hero_frequencies=plot_dict,
            axe=axe,
            **plot_style,
        )
        size = 0.6
        x_pos = 0.0
        y_pos = (ticks[0] + ticks[-1]) / 2.0
        # Add the hero ircon
        add_hero_icon(h, x_pos, y_pos, size, axe)
        offset += 3*plot_style['bargap']
        yticks += ticks
        ylabels += labels
        
    axe.set_yticks(yticks, ylabels)
    axe.yaxis.set_tick_params(pad=20)
    # Make legend manually
    # Player labels
    handles = []
    for p, cmap in plot_style['colour_map'].items():
        patch = mpatches.Patch(color=cmap(0), label=p)
        handles.append(patch)
    l1 = axe.legend(handles=handles)
    # Time labels
    time_cmap = mpl_colormaps.get('copper')
    handles_time = []
    for t, s in plot_style['plot_hatching'].items():
        patch = mpatches.Patch(facecolor=time_cmap(0), hatch=s, label=t, edgecolor='white')
        handles_time.append(patch)
    axe.add_artist(l1)
    axe.legend(
        handles = handles_time,
        ncol = 3,
        loc=(0.0, 0.0),
        bbox_transform=axe.transData
        )

    return fig