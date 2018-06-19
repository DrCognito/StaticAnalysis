def relativeCellCord(cell):
    return (cell - 64)/128


def relative_coordinate(cell, adjustment=0):
    return relativeCellCord(cell + adjustment/256.0)


def average_coorinates(coordinates):
    entries = 0
    tot_x = 0
    tot_y = 0
    for x, y in coordinates:
        tot_x += x
        tot_y += y
        entries += 1
    if entries == 0:
        return None
    return (tot_x/entries, tot_y/entries)
