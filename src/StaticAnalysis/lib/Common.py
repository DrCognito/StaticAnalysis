from sqlalchemy import not_, and_
from sqlalchemy.orm import Session
from typing import List
import matplotlib.image as mpimg
from os import environ as environment
import pandas as pd


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


# [x0, y0], [x1, y1]
radiant_ancient_cords = [[22/1024, 60/1024], [293/1024, 322/1024]]
dire_ancient_cords = [[714/1024, 666/1024], [993/1024, 975/1024]]

# [xMin, xMax, yMin, yMax] matches matplotlib "extent"
MAP_EXTENT_733_CALC = [6711.773778920308, 25817.172236503855, 7001.94459833795, 26096.127423822712]
MAP_EXTENT_733_MEASURED =  [7783.875000, 25120.000000, 7651.781250, 25227.125000]


def location_filter(location, Type):
    xmin = location[0][0]
    xmax = location[1][0]

    ymin = location[0][1]
    ymax = location[1][1]

    return not_(and_(Type.xCoordinate >= xmin, Type.xCoordinate <= xmax,
                Type.yCoordinate >= ymin, Type.yCoordinate <= ymax))


def seconds_to_nice(s):
    '''Converts s seconds to a nicely formatted min:sec string'''
    if s < 0:
        mins, sec = divmod(-1*s, 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "-{}:{}".format(mins, sec)
    else:
        mins, sec = divmod(s, 60)
        if sec < 10:
            sec = "0{}".format(sec)
        time = "{}:{}".format(mins, sec)

    return time


# Cache the retrieved player IDs.
player_cache = {}


def get_player_name(team_session: Session, steam_id: int, team) -> str:
    from StaticAnalysis.lib.team_info import TeamPlayer
    """Returns a known players name from a steamID.

    Arguments:
        team_session {Session} -- Open session to team_info DB.
        steam_id {int} -- 64-bit steamID.

    Raises:
        ValueError: If the steamID is not known.

    Returns:
        str -- Player name.
    """
    if steam_id in player_cache:
        return player_cache[f"{steam_id}_{team.team_id}"]

    player = team_session.query(TeamPlayer.name)\
                         .filter(and_(TeamPlayer.player_id == steam_id, TeamPlayer.team_id == team.team_id))\
                         .one_or_none()

    if player is None:
        print(f"Steam id {steam_id} not found for {team.name}.")
        player = team_session.query(TeamPlayer.name)\
                             .filter(TeamPlayer.player_id == steam_id)\
                             .first()
    if player is None:
        raise ValueError
    else:
        player_cache[f"{steam_id}_{team.team_id}"] = player[0]
        return player[0]


def get_player_map(team_session: Session, steam_ids: set, team)-> dict():
    """Takes a set of steam_ids and returns a dictionary map to their name.
    Unknown players are labeled as "Un" + an incrementing number.
    
    Arguments:
        team_session {Session} -- Open session to team_info DB.
        steam_ids {set} -- Set of 64bit steam IDS.
    
    Returns:
        dict -- Dictionary mapping steam ID to name or Un.
    """
    unknown_count = 0
    output = {}
    for i in steam_ids:
        try:
            output[i] = get_player_name(team_session, int(i), team)
        except ValueError:
            output[i] = "Un" + str(unknown_count)
            unknown_count += 1

    return output


def get_team(team_session: Session, team_name: str):
    from StaticAnalysis.lib.team_info import TeamInfo
    """Helper function to retrieve a team with a matched team name.
    
    Arguments:
        team_session {Session} -- Session for team_info DB
        team_name {str} -- String matching the team name in the DB.

    Raises:
    ValueError: If the team_name is not found.

    Returns:
        TeamInfo -- TeamInfo object.
    """
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == team_name).one_or_none()

    if team is None:
        raise ValueError("Team {} not found.".format(team))

    return team


def get_player_init(names: List[str])-> List[str]:
    """Attempt to automatically generate unique initials
    
    Arguments:
        names {List[str]} -- List of full names.
    
    Returns:
        List[str] -- List of initialisations. Duplicates become numbered.
    """
    # Try first two
    initials = {x:x[:2] for x in names}
    unique = set(list(initials.values()))
    if len(unique) == len(names):
        return initials

    # Ok got dups, correct them using numbers instead
    fixed = {}
    totals = {}
    unique = set()
    # for i, s in initials.iteritems():
    for i, s in initials.items():
        if s in totals:
            new_i = s
            while new_i in totals:
                totals[s] += 1
                new_i = s[0] + str(totals[s])
            fixed[i] = new_i
        else:
            totals[s] = 0
            fixed[i] = s

    return fixed


cell_size = 1/64
x_offset = 0.007997743856013796
x_scale = 0.9941107943899092
y_offset = -0.0007035503183143038
y_scale = 1.005702141386541


# Compared as of 13/09/2022, Patch 7.32
def add_map(axis, extent=[0, 1, 0, 1], zorder=0):
    img = mpimg.imread(environment['MAP_PATH'])
    axis.imshow(img, extent=extent, zorder=zorder)

    return axis


# https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
class ChainedAssignent:
    def __init__(self, chained=None):
        acceptable = [None, 'warn', 'raise']
        assert chained in acceptable, "chained must be in " + str(acceptable)
        self.swcw = chained

    def __enter__(self):
        self.saved_swcw = pd.options.mode.chained_assignment
        pd.options.mode.chained_assignment = self.swcw
        return self

    def __exit__(self, *args):
        pd.options.mode.chained_assignment = self.saved_swcw