from typing import List
from .Statistics import x_vs_time, xy_vs_time, cumulative_statistic
from pandas import DataFrame, Series, concat
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.PositionTimeBase import PositionTimeBase
from replays.Replay import Replay, Team
from replays.Rune import RuneID
from replays.Ward import Ward, WardType
from replays.TeamSelections import PickBans
from replays.Smoke import Smoke
from lib.team_info import TeamInfo
from sqlalchemy import and_
from datetime import timedelta
from lib.HeroTools import heroShortName


def win_rate_table(r_query, team):

    def _process_replays(r_in, side):
        firsttotal = 0
        firstwins = 0
        secondtotal = 0
        secondwins = 0

        for game in r_in:
            is_first = game.first_pick() == side
            if side == game.winner:
                if is_first:
                    firstwins += 1
                else:
                    secondwins += 1
            if is_first:
                firsttotal += 1
            else:
                secondtotal += 1
        output = Series()
        output['First Wins'] = firstwins
        output['First Losses'] = firsttotal - firstwins
        output['Second Wins'] = secondwins
        output['Second Losses'] = secondtotal - secondwins
        output['All Wins'] = output['First Wins'] + output['Second Wins']
        output['All Losses'] = output['First Losses'] + output['Second Losses']
        return output

    output = DataFrame(columns=['Dire', 'Radiant'])

    f_dire = Replay.get_side_filter(team, Team.DIRE)
    r_dire = r_query.filter(f_dire)
    output['Dire'] = _process_replays(r_dire, Team.DIRE)

    f_radiant = Replay.get_side_filter(team, Team.RADIANT)
    r_radiant = r_query.filter(f_radiant)
    output['Radiant'] = _process_replays(r_radiant, Team.RADIANT)
    output['All'] = output['Dire'] + output['Radiant']
    output.loc['First Pick'] = output.loc['First Wins']/\
                               (output.loc['First Wins'] + output.loc['First Losses'] )
    output.loc['Second Pick'] = output.loc['Second Wins']/\
                               (output.loc['Second Wins'] + output.loc['Second Losses'] )
    output.loc['All'] = output.loc['All Wins']/\
                               (output.loc['All Wins'] + output.loc['All Losses'] )

    return output.T


def simple_side_filter(r_query, session, team: TeamInfo,
                       Type, side: Team, extra_filter=None,
                       limit=None):
    r_filter = Replay.get_side_filter(team, side)
    #replays = r_query.filter(r_filter).subquery()
    replays = r_query.filter(r_filter)
    if limit:
        replays = replays.limit(limit)

    typeFilter = Type.team.__eq__(side)
    if extra_filter is not None:
        # w_query = session.query(Type).filter(and_(Type.Team == side, extra_filter))\
        #                              .join(replays)
        typeFilter = and_(typeFilter, extra_filter)
    # else:
    #     w_query = session.query(Type).join(replays)
    w_query = session.query(Type).join(replays).filter(typeFilter)
    return w_query


def get_smoke(r_query, session, team: TeamInfo):
    dire = simple_side_filter(r_query, session, team, Smoke, Team.DIRE)
    radiant = simple_side_filter(r_query, session, team, Smoke, Team.RADIANT)

    return dire, radiant


def get_side_replays(r_query, session, team: TeamInfo):
    dire_filter = Replay.get_side_filter(team, Team.DIRE)
    radiant_filter = Replay.get_side_filter(team, Team.RADIANT)

    dire = r_query.filter(dire_filter)
    radiant = r_query.filter(radiant_filter)

    return dire, radiant


def hero_win_rate(r_query, team, limit=None):
    output = DataFrame(columns=['Win', 'Loss'])

    replays = r_query.order_by(Replay.replayID.desc())
    if limit is not None:
        replays = replays.limit(limit)

    for r in replays:
        if r.teams[0].teamID == team.team_id and r.teams[0].stackID == team.stack_id:
            team_num = 0
        else:
            team_num = 1
        
        is_win = r.winner == r.teams[team_num].team

        picks = [p.hero for p in r.teams[team_num].draft if p.is_pick]

        for hero in picks:
            column = 'Win' if is_win else 'Loss'

            if hero in output[column]:
                output.loc[hero, column] += 1
            else:
                output.loc[hero, column] = 1
                other_col = 'Loss' if is_win else 'Win'
                output.loc[hero, other_col] = 0

    output.fillna(0, inplace=True)
    output['Total'] = output['Win'] + output['Loss']
    output['Rate'] = output['Win']/output['Total']

    return output


def get_ptbase_tslice(session, r_query, Type,
                      team: TeamInfo, start=None, end=None,
                      replay_limit=None):
    if start is not None and end is not None:
        assert(end >= start)
        t_filter = and_(Type.game_time > start, Type.game_time <= end)
    elif start is not None:
        t_filter = Type.game_time > start
    elif end is not None:
        t_filter = Type.game_time <= end
    else:
        t_filter = None

    dire = simple_side_filter(r_query, session, team, Type, Team.DIRE,
                              t_filter, limit=replay_limit)
    radiant = simple_side_filter(r_query, session, team, Type, Team.RADIANT,
                                 t_filter, limit=replay_limit)

    return dire, radiant


def get_ptbase_tslice_side(session, r_query, Type,
                           team: TeamInfo,
                           side: Team,
                           start=None, end=None):
    if start is not None and end is not None:
        assert(end >= start)
        t_filter = and_(Type.game_time > start, Type.game_time <= end)
    elif start is not None:
        t_filter = Type.game_time > start
    elif end is not None:
        t_filter = Type.game_time <= end
    else:
        t_filter = None

    if side == Team.DIRE:
        out = simple_side_filter(r_query, session, team, Type, Team.DIRE,
                                 t_filter)
    else:
        out = simple_side_filter(r_query, session, team, Type, Team.RADIANT,
                                 t_filter)

    return out


def get_rune_control(r_query, team: TeamInfo):
    '''Gets runes collected over time for team and opposition.'''
    runes_bounty_opp = Series()
    runes_power_opp = Series()
    runes_bounty_team = Series()
    runes_power_team = Series()

    # Establish base line to help rebinning consistently
    runes_bounty_opp[timedelta(seconds=0)] = 0
    runes_power_opp[timedelta(seconds=0)] = 0
    runes_bounty_team[timedelta(seconds=0)] = 0
    runes_power_team[timedelta(seconds=0)] = 0

    match: Replay
    for match in r_query:
        if match.teams[0].teamID == team.team_id or\
           match.teams[0].stackID == team.stack_id:
            team_side = match.teams[0].team
        elif match.teams[1].teamID == team.team_id or\
             match.teams[1].stackID == team.stack_id:
            team_side = match.teams[1].team
        else:
            raise ValueError("Could not find team {} in replay {}"
                             .format(team.name, match.replayID))

        for rune in match.runes:
            def _increment(time, series):
                time = timedelta(seconds=time)
                if time in series:
                    series[time] += 1
                else:
                    series[time] = 1

            is_bounty = rune.runeType == RuneID.Bounty or rune.runeType == RuneID.WaterRune

            if is_bounty:
                if rune.team == team_side:
                    _increment(rune.game_time, runes_bounty_team)
                else:
                    _increment(rune.game_time, runes_bounty_opp)
            else:
                if rune.team == team_side:
                    _increment(rune.game_time, runes_power_team)
                else:
                    _increment(rune.game_time, runes_power_opp)

    data = [runes_bounty_team, runes_bounty_opp,
            runes_power_team, runes_power_opp]
    columns = ["Team Bounty", "Opposition Bounty",
               "Team Power", "Opposition Power"]

    output = concat(data, axis=1)
    output.columns = columns

    return output


def pair_rate(session, r_query, team, limit=None):
    output = {}

    def _pairs_by_side(pick_bans: List[PickBans]):
        last_team = None
        last_was_pick = None
        last_hero = None
        last_order = -99
        pick_pair_ordinal = 0
        dire_out = {}
        radiant_out = {}
        for p in pick_bans:
            team = p.team
            hero = p.hero
            is_pick = p.is_pick
            order = p.order
            # If its the same team, a pick and last one was a pick, thats a pair!
            if last_team == team and is_pick and last_was_pick and order == last_order + 1:
                sorted = [last_hero, hero]
                sorted.sort()
                if team == Team.DIRE:
                    dire_out[pick_pair_ordinal] = f"{sorted[0]}, {sorted[1]}"
                if team == Team.RADIANT:
                    radiant_out[pick_pair_ordinal] = f"{sorted[0]}, {sorted[1]}"
                pick_pair_ordinal += 1
            # Variables for next go round
            last_team = team
            last_was_pick = is_pick
            last_hero = hero
            last_order = order

        return dire_out, radiant_out

    r_query = r_query.order_by(Replay.replayID.desc())
    if limit is not None:
        r_query = r_query.limit(limit)

    for replay in r_query:
        all_picks = session.query(PickBans)\
                           .filter(PickBans.replayID == replay.replayID)\
                           .order_by(PickBans.order)\
                           .all()
        for t in replay.teams:
            if t.teamID != team.team_id and t.stackID != team.stack_id:
                continue

            dire, radiant = _pairs_by_side(all_picks)
            if t.team == Team.DIRE:
                pick_pairs = dire
            if t.team == Team.RADIANT:
                pick_pairs = radiant
            for i, pair in pick_pairs.items():
                if i not in output:
                    output[i] = Series()
                if pair in output[i]:
                    output[i][pair] += 1
                else:
                    output[i][pair] = 1

    for out in output:
        output[out].sort_values(ascending=False, inplace=True)

    return output


def draft_summary(session, r_query, team, limit=None) -> (DataFrame, DataFrame):
    '''Returns a count of picks and bans at each draft stage for team.
       Return type is Pandas DataFrame.
    '''

    output_pick = DataFrame()
    output_ban = DataFrame()

    r_query = r_query.order_by(Replay.replayID.desc())
    if limit is not None:
        r_query = r_query.limit(limit)

    team_res = (t for r in r_query for t in r.teams)
    # replay = (t.draft for r in replays for t in r.teams if t.team == side)
    # for replay in replays:
    #     for t in replay.team:

    for t in team_res:
        if t.teamID != team.team_id and t.stackID != team.stack_id:
            continue
        # for draft in t.draft:
        picks = {}
        bans = {}
        pick_count = 0
        ban_count = 0

        for selection in t.draft:
            if selection.is_pick:
                column = "Pick" + str(pick_count)
                picks[column] = selection.hero
                pick_count += 1
            else:
                column = "Ban" + str(ban_count)
                bans[column] = selection.hero
                ban_count += 1

        output_pick = output_pick.append(picks, ignore_index=True)
        output_ban = output_ban.append(bans, ignore_index=True)

    output_pick = output_pick.apply(Series.value_counts)
    output_ban = output_ban.apply(Series.value_counts)

    return output_pick, output_ban


short_alphabetical_names = sorted(heroShortName.values())


def counter_picks(session, r_query, team) -> DataFrame:
    """Produces a table of counter picks. Information on how a team picks heroes
    following selection of others by the opposition.

    Arguments:
        session {} -- Replay DB session.
        r_query {} -- DB query for the replays used.
        team {TeamInfo} -- Team that data is gathered for.

    Returns:
        DataFrame -- [opp_picks vs team picks] includes 0s.
    """
    counters = DataFrame(columns=short_alphabetical_names,
                         index=short_alphabetical_names)
    counters = counters.fillna(0)

    def _process(side):
        side_filt = Replay.get_side_filter(team, side)
        replays = r_query.filter(side_filt)

        r: Replay
        for r in replays:
            draft = []
            selection: PickBans
            for selection in (r.teams[0].draft + r.teams[1].draft):
                draft.append(
                    {"hero": selection.hero,
                     "is_pick": selection.is_pick,
                     "side": selection.team,
                     "order": selection.order}
                )
            draft = sorted(draft, key=lambda k: k['order'])
            opp_picks = []
            for pick_ban in draft:
                if not pick_ban['is_pick']:
                    continue
                name = heroShortName[pick_ban['hero']]
                if pick_ban['side'] == side:
                    for o in opp_picks:
                        counters[name][o] += 1
                else:
                    opp_picks.append(name)
        return

    _process(Team.DIRE)
    _process(Team.RADIANT)

    return counters
