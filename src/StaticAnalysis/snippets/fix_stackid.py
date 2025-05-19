from StaticAnalysis import session
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TeamSelections import TeamSelections, get_stack_id

# Default is '' when a team is player less
broken_selections = session.query(TeamSelections).filter(TeamSelections.stackID == '')

ts: TeamSelections
for ts in broken_selections:
    ts.stackID = get_stack_id(ts.replay, ts.team)
    session.merge(ts)
session.commit()