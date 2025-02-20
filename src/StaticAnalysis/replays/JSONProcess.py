'''Utility functions for retrieving information
   from processed replays in JSON format
'''
from StaticAnalysis.replays.Common import Team


def get_pick_ban(json_in):
    return [x for x in json_in if x['type'] == 'PicksAndBans'][0]


def get_replay_id(json_in, path):
    ''' Returns the replayID as reported by the file.
        Note: there have been instances of this being wrongly set to 0
    '''
    pick_ban_object = get_pick_ban(json_in)
    replay_id = pick_ban_object.get('matchID', None)

    if replay_id == 0 or replay_id is None:
            print("Warning, replay {} has an invalid replay ID".format(path))
            replay_id = path.stem

    return int(replay_id)


def get_end_time_UTC(json_in):
    ''' Returns the end time in unix format from the json file.'''
    pick_ban_object = get_pick_ban(json_in)
    return pick_ban_object['endTimeUTC']


def get_match_times(json_in):
    '''Return the start time, creep spawn time
       and end game time as a timedelta.'''
    time_entry = [x for x in json_in if x['type'] == 'TimeInfo']

    if not time_entry:
        return (None, None, None)
    game_start = round(time_entry[0]['PreGameStart'])

    creep_spawn = round(time_entry[0]['CreepSpawn'])

    end_time = round(time_entry[0]['GameEndTime'])

    return (game_start, creep_spawn, end_time)


def get_winner(json_in):
    '''Return the winner of the game, 2 = Radiant, 3 = Dire.
       Input is json string'''
    pick_ban_object = get_pick_ban(json_in)
    return Team(pick_ban_object['winningTeam'])


def get_wards(json_in):
    '''Returns all the wards for further processing. '''
    yield from (x for x in json_in if x['type'] == 'ward' and x['entLeft'] == False)


def get_player_positions(hero, json_in):
    for x in json_in:
        if x['type'] == "HeroEntity" and x['cName'] == hero:
            for y in zip(x['xPos'], x['yPos']):
                yield y


def get_player_status(hero, json_in):
    for x in json_in:
        if x['type'] == "HeroEntity" and x['cName'] == hero:
            for y in zip(x['xPos'], x['yPos'], x['smoked'], x['alive']):
                yield y


def get_player_created(hero, json_in):
    created_time = next((x['createdTime'] for x in json_in if x['type'] ==
                        "HeroEntity" and x['cName'] == hero), None)
    return created_time


def get_player_smoketime(hero, json_in):
    smoke_starts = next((x['smokeStart'] for x in json_in if x['type'] ==
                        "HeroEntity" and x['cName'] == hero), None)

    smoke_ends = next((x['smokeEnd'] for x in json_in if x['type'] ==
                      "HeroEntity" and x['cName'] == hero), None)

    return zip(smoke_starts, smoke_ends)


def get_player_team(hero, json_in):
    team_name = next((x['entType'] for x in json_in if x['type'] ==
                     "HeroEntity" and x['cName'] == hero), None)

    if team_name == "DIRE":
        team = Team.DIRE
    elif team_name == "RADIANT":
        team = Team.RADIANT
    else:
        raise ValueError("Invalid team name, {}, in hero, {}"
                         .format(team_name, hero))

    return team


def get_scans(json_in):
    return next((x for x in json_in if x['type'] == "ScanSummary"), None)


def get_rune_list(json_in):
    return next((x['runeList'] for x in json_in if x['type'] == "runeList"), None)


def get_accumulating_lists(hero, json_in):
    assists = next((x['assistList'] for x in json_in if x['type'] ==
                   "HeroEntity" and x['cName'] == hero), None)
    deaths = next((x['deathList'] for x in json_in if x['type'] ==
                  "HeroEntity" and x['cName'] == hero), None)
    denies = next((x['denyList'] for x in json_in if x['type'] ==
                  "HeroEntity" and x['cName'] == hero), None)
    kills = next((x['killList'] for x in json_in if x['type'] ==
                 "HeroEntity" and x['cName'] == hero), None)
    last_hits = next((x['last_hitList'] for x in json_in if x['type'] ==
                      "HeroEntity" and x['cName'] == hero), None)

    return {'assists': assists, 'deaths': deaths, 'denies': denies,
            'kills': kills, 'last_hits': last_hits}


def get_net_worth(hero, json_in):
    for x in json_in:
        if x['type'] == "HeroEntity" and x['cName'] == hero:
            if 'net_worth' not in x:
                raise ValueError(f"Missing networth for {hero}")
                # return []
            return x['net_worth']
    raise ValueError(f"Hero not found {hero}")
    # return next((x['net_worth'] for x in json_in if x['type'] == "HeroEntity" and x['cName'] == hero), None)


def get_smoke_summary(json_in, team):
    assert(team in Team)
    smoke_summary = next((x for x in json_in if x['type'] == 'SmokeSummary'), None)
    if team == Team.DIRE:
        start = 'direSmokes'
        end = 'direSmokesEnd'
    elif team == Team.RADIANT:
        start = 'radiantSmokes'
        end = 'radiantSmokesEnd'
    if smoke_summary is None:
        return None
    return zip(smoke_summary[start], smoke_summary[end])


def get_tormentor_summary(json_in):
    for x in json_in:
        if x['type'] == 'TormentorSummary':
            return x
    return {}


def get_league_id(json_in):
    pick_ban = get_pick_ban(json_in)

    return pick_ban['leagueID']
