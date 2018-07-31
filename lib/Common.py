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


radiant_fountain_cords = [[22/1024, 60/1024], [117/1024, 157/1024]]
radiant_ancient_cords = [[22/1024, 60/1024], [293/1024, 322/1024]]
dire_fountain_cords = [[901/1024, 879/1024], [993/1024, 975/1024]]
dire_ancient_cords = [[714/1024, 666/1024], [993/1024, 975/1024]]
