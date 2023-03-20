import pstats
from pstats import SortKey

p = pstats.Stats('do_pos')
tid = p.sort_stats(SortKey.TIME)
tid.print_stats(10)