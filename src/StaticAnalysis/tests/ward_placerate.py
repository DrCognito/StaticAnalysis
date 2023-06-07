from StaticAnalysis.tests.minimal_db import session, team_session, TeamInfo
from StaticAnalysis.replays.Replay import Replay, Team
from StaticAnalysis.analysis.ward_vis import plot_image_scatter
from StaticAnalysis.analysis.Replay import get_ptbase_tslice
from StaticAnalysis.analysis.visualisation import dataframe_xy_time
from StaticAnalysis.replays.Ward import Ward, WardType
import matplotlib.pyplot as plt
from herotools.important_times import ImportantTimes

replay_limit = 20  # !?
team_liquid: TeamInfo
team_liquid = team_session.query(TeamInfo).filter(TeamInfo.team_id == 2163).one()
cut_time = ImportantTimes['After_Berlin']

r_filter = Replay.endTimeUTC >= cut_time
r_query = team_liquid.get_replays(session).filter(r_filter)
team = team_liquid

wards_dire, wards_radiant = get_ptbase_tslice(session, r_query, team=team,
                                              Type=Ward,
                                              start=-2*60, end=12*60,
                                              replay_limit=replay_limit)
wards_dire = wards_dire.filter(Ward.ward_type == WardType.OBSERVER)
wards_radiant = wards_radiant.filter(Ward.ward_type == WardType.OBSERVER)

dire_df = dataframe_xy_time(wards_dire, Ward, session)
radiant_df = dataframe_xy_time(wards_radiant, Ward, session)
