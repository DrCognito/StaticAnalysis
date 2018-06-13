from pandas import DataFrame, Series
from datetime import timedelta


# def cumulative_statistic(properties, index=None, conversion=None):
#     '''Returns a pandas Series for the property in collection.
#        Index is used to generate the Series index.
#        Conversion is a function that converts property to the desired format'''
#     output = Series()

#     for p in properties:
        


def x_vs_time(collection_methods, start=0, end=None, conversion=None):
    '''Returns a pandas Series for the property in collection over time.
       Property is a function that accepts a time parameter.
       Index is time.
       Conversion is a function that converts property to the desired format'''
    output = Series()

    for method in collection_methods:
        time_it = range(start) if end is None else range(start, end)
        for i in time_it:
            x = method(i)
            if conversion is not None:
                x = conversion(x)
            output[timedelta(seconds=i)] = x

    return output


def xy_vs_time(collection_methods, start=0, end=None, conversion=None):
    '''Returns a pandas DataFrame for the property in collection over time.
       collection_methods is a list of function that accepts a time
       parameter and returns (x,y).
       Index is time.
       Conversion is a function that converts property to the desired format'''
    output = DataFrame(columns=['x', 'y'])

    for method in collection_methods:
        time_it = range(start) if end is None else range(start, end)
        for i in time_it:
            x, y = method(i)
            if conversion is not None:
                x, y = conversion(x, y)
            output.loc[timedelta(seconds=i)] = [x, y]

    return output
