from StaticAnalysis.tests.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.replays.Player import Player, NetWorth
from pandas import DataFrame, read_sql

test_replay = 7290518726

r_query = session.query(NetWorth).filter(NetWorth.replayID == test_replay)
# t_query = r_query.filter(NetWorth.game_time == 600).with_entities(NetWorth.hero, NetWorth.networth)
b_query = session.query(NetWorth).filter(NetWorth.replayID == test_replay, NetWorth.game_time == 600)
# test = b_query.with_entities(NetWorth.hero, NetWorth.networth)
df = read_sql(b_query.statement, session.bind)