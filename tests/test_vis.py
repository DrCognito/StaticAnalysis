import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.draft_vis import replay_draft_image
from Setup import get_team_session, get_testDB
from lib.team_info import TeamInfo
from replays.Replay import Replay, Team
from replays.TeamSelections import TeamSelections

team_session = get_team_session()
s_maker = get_testDB()
session = s_maker()

Teams = {
    'Mad Lads': team_session.query(TeamInfo)
                            .filter(TeamInfo.team_id == 5229049).one()
}

t_filter = Teams['Mad Lads'].filter
r_query = Teams['Mad Lads'].get_replays(session)
print("Total replays for team: {}".format(r_query.count()))
r_test = session.query(Replay).filter(t_filter).outerjoin(TeamSelections).filter(TeamSelections.draft.any())
# r_query = r_query.filter(~Replay.teams.draft.any())
print("Total replays for team excluding missing drafts: {}".format(len(r_test.all())))
dire_filter = Replay.get_side_filter(Teams['Mad Lads'], Team.DIRE)
radiant_filter = Replay.get_side_filter(Teams['Mad Lads'], Team.RADIANT)

dire_drafts = replay_draft_image(r_test.filter(dire_filter).all(),
                                 Team.DIRE,
                                 'Mad Lads')

dire_drafts.save("dire_draft.png")

radiant_drafts = replay_draft_image(r_test.filter(radiant_filter).all(),
                                    Team.RADIANT,
                                    'Mad Lads')
radiant_drafts.save("radiant_draft.png")