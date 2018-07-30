import matplotlib.pyplot as plt
import numpy as np

import SummaryStatistics as sstat
from analysis.visualisation import (plot_hexbin_time, plot_map_points,
                                    plot_player_heroes)

# picks = sstat.test_player_picks()
# fig, extra = plot_player_heroes(picks)
# fig.tight_layout(h_pad=3.0)
# fig.savefig('PlayerPicks.png',
#             bbox_extra_artists=extra,
#             bbox_inches='tight')

p5_pos = sstat.test_player_position()

def test_plot(query):
    p5_heatmap, xedges, yedges = plot_map_points(query)
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    heatmap_masked = np.ma.masked_where(p5_heatmap == 0, p5_heatmap)
    percentiles = [70, 99.9]
    _min, _max = np.nanpercentile(heatmap_masked.filled(np.nan), percentiles)
    #plt.imshow(heatmap_masked, extent=extent, interpolation='none', vmin=_min, vmax=_max)
    plt.imshow(heatmap_masked, extent=extent, zorder=1, alpha=1.0,
               vmin=_min, vmax=_max, interpolation='none')

test_plot(p5_pos[0])
test_plot(p5_pos[1])
