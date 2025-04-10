from StaticAnalysis.analysis.draft_vis import (hero_box_image, hero_box_image_portrait,
                                process_team_dotabuff, process_team_portrait,
                                process_team_portrait_dotabuff,
                                replay_draft_image, pickban_line_image)
from StaticAnalysis.lib.team_info import InitTeamDB, TeamInfo, TeamPlayer
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis import team_session, session



def get_team(name):
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == name).one_or_none()

    return team


team = get_team("Team Spirit")
r_query = team.get_replays(session).filter(Replay.replayID == 8248178512)

replay: Replay = r_query.first()

for t in replay.teams:
    if t.team == Team.DIRE:
        radiant_old = process_team_portrait(replay, t)
        radiant = process_team_portrait_dotabuff(replay, t)
        radiant2 = process_team_dotabuff(replay, t)
    else:
        dire = process_team_portrait_dotabuff(replay, t)
        dire2 = process_team_dotabuff(replay, t)

full_line = pickban_line_image(replay, team, add_team_name=True)

# radiant2.show()
# dire2.show()
full_line.show()
# radiant.save('./rtest.png')
# dire.save('./dtest.png')

# test = hero_box_image_portrait("npc_dota_hero_viper", is_pick=True, pick_num=10)
# test = replay_draft_image([replay,], Team.RADIANT, 'Hippomaniacs')
# test.show()
