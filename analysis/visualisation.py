import numpy as np
from pandas import DataFrame, read_sql

def plot_map_points(query, bins=128):
    coordinates = ((q.xCoordinate, q.yCoordinate) for q in query)

    heatmap, _, _ = np.histogram2d(*coordinates, bins=bins,
                                   range=[[0, 1], [0, 1]], normed=False)

    return heatmap


def plot_hexbin_time(query, Type, session, bin_size=128):
    sql_query = query.with_entities(Type.xCoordinate,
                                    Type.yCoordinate,
                                    Type.time).statement

    data = read_sql(sql_query, session.bind)

    return data