from StaticAnalysis import session, team_session, LOG
from StaticAnalysis.lib.team_info import TeamInfo,get_team
from StaticAnalysis.replays.Replay import Replay
from StaticAnalysis.replays.TeamSelections import TeamSelections
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


def remap_team(
    current_team: TeamInfo | int, to_team: TeamInfo | int,
    session: Session, filter=None):
    # Ensure we have our team_ids
    if type(current_team) is TeamInfo:
        current_team = current_team.team_id
    if type(to_team) is TeamInfo:
        to_team = to_team.team_id

    query = session.query(TeamSelections).filter(
        TeamSelections.teamID == current_team
    )
    if filter is not None:
        query = query.filter(filter)
    LOG.info(f"Remapping {query.count()} TeamSelections.")
    for ts in query.all():
        LOG.info(f"Remaping {ts.replay_ID} from {current_team} to {to_team}.")
        ts.teamID = to_team
    try:
        session.commit()
    except SQLAlchemyError as e:
        LOG.opt(exception=True).error(e)
        session.rollback()
        exit(2)

remap_team(9017006, 36, session)

def stack_stats(stack_id: TeamInfo | str, team_match: TeamInfo | int):
    if type(stack_id) is TeamInfo:
        stack_id = stack_id.stack_id
    if type(team_match) is TeamInfo:
        team_match = team_match.team_id

    query_all = session.query(TeamSelections).filter(
        TeamSelections.stackID == stack_id
    )
    query_mismatch = session.query(TeamSelections).filter(
        TeamSelections.stackID == stack_id, TeamSelections.teamID != team_match
    )
    LOG.info(f"Total stack matches: {query_all.count()}. With wrong team ID: {query_mismatch.count()}")
    
navi = get_team(36)
stack_stats(navi, navi)