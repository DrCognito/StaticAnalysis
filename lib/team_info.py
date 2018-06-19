from collections import OrderedDict
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from replays.Replay import Replay
from replays.TeamSelections import TeamSelections
from sqlalchemy import or_


class TeamInfo():
    def __init__(self, name, players, team_id=None, filt=None):
        '''name: Team name.
           players: OrderedDict of player names: steam_ids.
           team_id: Numerical team_id, will be used to get replays
           if filter undefined.
           filt: SqlAlchemy filter to identify team replays.
           One of filt or team_id must be defined.
        '''
        self.name = name
        self.player_ids = players
        self._filter = filt
        self.team_id = team_id

        if self.team_id is None and self._filter is None:
            raise ValueError("TeamInfo class must be defined with at least a filter or team_id.")

    @property
    def stack_id(self):
        ids = list()
        for name in self.player_ids:
            ids.append(self.player_ids[name])

        ids.sort()

        return ''.join(str(i) for i in ids)

    @property
    def filter(self):
        if self._filter is None:
            id_filter = Replay.teams.any(TeamSelections.teamID == self.team_id)
            stack_filter = Replay.teams.any(TeamSelections.stackID == self.stack_id)
            self._filter = or_(id_filter, stack_filter)

        return self._filter

    def replay_count(self, session):
        return session.query(Replay).filter(self.filter).count()

    def get_replays(self, session, additional_filter=None):
        if additional_filter is None:
            return session.query(Replay).filter(self.filter)
        else:
            return session.query(Replay).filter(self.filter)\
                                        .filter(additional_filter)


Teams = {}
TeamIDs = {}
PlayerIDs = {}

PlayerIDs['Mad Lads'] = OrderedDict()
PlayerIDs['Mad Lads']['Qojkva'] = 76561198047004422
PlayerIDs['Mad Lads']['Madara'] = 76561198055695796
PlayerIDs['Mad Lads']['Khezu'] = 76561198129291346
PlayerIDs['Mad Lads']['MaybeNextTime'] = 76561198047219142
PlayerIDs['Mad Lads']['Synderen'] = 76561197964547457
TeamIDs['Mad Lads'] = 5229049
Teams['Mad Lads'] = TeamInfo(name='Mad Lads', players=PlayerIDs['Mad Lads'],
                             team_id=TeamIDs['Mad Lads'])
