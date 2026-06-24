from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import MappedAsDataclass
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select, distinct, BigInteger
from herotools.lib.position import Position
from StaticAnalysis import CONFIG, LOG
from StaticAnalysis.analysis.Player import player_positioning_replay, closest_tower
from StaticAnalysis.analysis.networth import scheme_log, scheme_geo
from StaticAnalysis.replays.Player import NetWorth, PlayerStatus
from pandas import DataFrame, read_sql
from StaticAnalysis.replays.Replay import Team
from StaticAnalysis.lib.Common import dire_towers, radiant_towers
from itertools import chain
from sqlalchemy.exc import SQLAlchemyError


class DataClassBase(MappedAsDataclass, DeclarativeBase):
    """subclasses will be converted to dataclasses"""


class RolePosition(DataClassBase):
    __tablename__ = "role_position"
    
    replayID: Mapped[int] = mapped_column(primary_key=True)
    steamID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    position: Mapped[Position] = mapped_column(nullable=True)
    side: Mapped[Team]


def get_unique_replayids(session: Session) -> set[int]:
    '''
    Get the unique replay ids from role_position in session.
    '''
    query = select(distinct(RolePosition.replayID))
    return set(session.scalars(query))


def get_lane_info(
    session: Session, replay_id: int,
    time_limit: int = 7 * 60, scheme=scheme_log) -> DataFrame:
    '''
    Returns a DataFrame of steamIDs split by team showing their closest and next closest tower
    up to time_limit and networth at time_limit.
    '''
    

    # We asign lanes by player positioning
    player_pos = player_positioning_replay(session, replay_id, start=0, end=time_limit, alive_only=True)
    player_pos = player_pos.with_entities(PlayerStatus.steamID,
                                          PlayerStatus.xCoordinate,
                                          PlayerStatus.yCoordinate,
                                          PlayerStatus.team)

    pos_df = read_sql(player_pos.statement, session.bind)
    if pos_df.empty:
        return pos_df

    # Asign a lane for each time position
    def _asign_lane(row):
        x = row['xCoordinate']
        y = row['yCoordinate']
        if row['team'] == Team.DIRE:
            tower_dict = dire_towers
        if row['team'] == Team.RADIANT:
            tower_dict = radiant_towers

        return closest_tower((x, y), tower_dict, scheme=scheme)
    
    def _get_networth(row):
        query = select(NetWorth.networth).where(
            NetWorth.replayID == replay_id,
            NetWorth.steamID == row,
            NetWorth.game_time == time_limit
        )
        worth = session.scalar(query)

        return worth
    
    pos_df['lane'] = pos_df.apply(_asign_lane, axis=1)
    first = pos_df.groupby(by=['team', 'steamID',])['lane'].apply(lambda x: x.value_counts().index[0])
    # second = pos_df.groupby(by=['team', 'steamID',])['lane'].apply(lambda x: x.value_counts().index[1])
    # lanes = DataFrame({'1st':first, '2nd':second})
    lanes = DataFrame({'1st':first})
    lanes['NetWorth'] = lanes.index.get_level_values('steamID').map(_get_networth)
    
    return lanes


def pos_team_whole(df: DataFrame):
    output = {}
    if len(df) != 5:
        LOG.error("Incorrect number of players to assign potion!")
        return output
    
    df = df.sort_values(['1st', 'NetWorth'], ascending=False)
    # Assign the carries to each lane as top networth
    # Mid
    try:
        mid = df.loc[df['1st'] == 'mid'].iloc[0].name
        output[mid] = Position.MID
    except IndexError:
        LOG.debug("Could not assign mid")
        pass
    # Safe
    try:
        safe = df.loc[df['1st'] == 'safe'].iloc[0].name
        output[safe] = Position.SAFE
        p5 = df.loc[df['1st'] == 'safe'].iloc[1].name
        output[p5] = Position.P5
    except IndexError:
        LOG.debug("Could not assign safelaners")
        pass
    # Off
    try:
        off = df.loc[df['1st'] == 'off'].iloc[0].name
        output[off] = Position.OFF
        p4 = df.loc[df['1st'] == 'off'].iloc[1].name
        output[p4] = Position.P4
    except IndexError:
        LOG.debug("Could not assign offlaners")
        pass
    
    return output


def get_player_position(session: Session, steamID: int, replay_id: int):
    qry = select(RolePosition).where(
        RolePosition.steamID == steamID,
        RolePosition.replayID == replay_id
        )
    
    return session.execute(qry).scalar_one_or_none()

def add_replay_positions(
    session: Session, replay_id:int, time_limit: int = 7*60) -> list[RolePosition] | None:
    '''
    Using data from session for replay_id, assess the role position of the players up to time_limit.
    time_limit defaults to 7 minutes in game time.
    '''
    LOG.debug(f"Processing role positions for {replay_id}")
    # Get initial results
    lane_results = get_lane_info(session, replay_id, time_limit)
    if lane_results.empty:
        return
    # Estimate positions for each team
    radiant = pos_team_whole(lane_results.loc[Team.RADIANT])
    dire = pos_team_whole(lane_results.loc[Team.DIRE])
    
    if len(radiant) != 5 or len(dire) != 5:
        LOG.error(f"Could not process role positions for {replay_id}, incorrect number of results.")
        LOG.debug(f"Results radiant: {radiant}")
        LOG.debug(f"Results dire: {dire}")
        
        return
    
    try:
        positions = [
            RolePosition(replay_id, int(p), pos, Team.RADIANT) for p, pos in
            radiant.items()
        ]
        positions += [
            RolePosition(replay_id, int(p), pos, Team.DIRE) for p, pos in
            dire.items()
        ]
        assert len(positions) == 10
        session.add_all(positions)
    except AssertionError:
        LOG.error(f"Duplicater players in role position processing after combining teams!")
        LOG.debug(f"Results radiant: {radiant}")
        LOG.debug(f"Results dire: {dire}")
        return
    except SQLAlchemyError as e:
        LOG.opt(exception=True).error(f"Failed to RolePositions for {replay_id}")
        session.rollback()

    return positions


# Basic DB management
def InitDB(path):
    engine = create_engine(path, echo=False)
    RolePosition.metadata.create_all(engine)

    return engine

# Builds the DB if none existent at path!
if __name__ == "__main__":
    try:
        DB_PATH = CONFIG['database']['PARSED_DB_PATH']
    except KeyError:
        print(f"Failed getting database path parameter in config.")
        
    InitDB(DB_PATH)