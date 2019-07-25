import Setup
import os
import sys
from os import environ as environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
from analysis.draft_vis import hero_box_image, process_team_portrait, hero_box_image_portrait, replay_draft_image
from replays.Replay import Replay, Team
from lib.team_info import InitTeamDB, TeamInfo, TeamPlayer

# DB Setups
session = Setup.get_fullDB()
team_session = Setup.get_team_session()
load_dotenv(dotenv_path="../setup.env")


def get_team(name):
    team = team_session.query(TeamInfo)\
                       .filter(TeamInfo.name == name).one_or_none()

    return team


team = get_team("Chaos Esports")
r_query = team.get_replays(session).filter(Replay.replayID == 4903243468)

replay: Replay = r_query.first()

for t in replay.teams:
    if t.team == Team.RADIANT:
        radiant = process_team_portrait(replay, t)
    else:
        dire = process_team_portrait(replay, t)


radiant.save('./rtest.png')
dire.save('./dtest.png')

# test = hero_box_image_portrait("npc_dota_hero_viper", is_pick=True, pick_num=10)
# test = replay_draft_image([replay,], Team.RADIANT, 'Hippomaniacs')
test.show()