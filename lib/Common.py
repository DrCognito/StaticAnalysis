from sqlalchemy import not_, and_
from sqlalchemy.orm import Session
from typing import List


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


def get_player_name(team_session: Session, steam_id: int) -> str:
    from lib.team_info import TeamPlayer, TeamInfo
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
        return player_cache[steam_id]

    player = team_session.query(TeamPlayer.name)\
                         .filter(TeamPlayer.player_id == steam_id)\
                         .first()

    if player is None:
        print("Steam id {} not found.".format(steam_id))
        raise ValueError
    else:
        player_cache[steam_id] = player[0]
        return player[0]


def get_player_map(team_session: Session, steam_ids: set)-> dict():
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
            output[i] = get_player_name(team_session, int(i))
        except ValueError:
            output[i] = "Un" + str(unknown_count)
            unknown_count += 1

    return output


def get_team(team_session: Session, team_name: str):
    from lib.team_info import TeamInfo
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
    for i, s in initials.iteritems():
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