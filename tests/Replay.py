import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from replays.Replay import populate_from_JSON_file, InitDB
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from replays.Replay import Replay
from replays.Player import Player, Kills, Deaths, Denies, Assists
from replays.Smoke import Smoke
from replays.TeamSelections import TeamSelections
from replays.Ward import Ward
from replays.Scan import Scan
from replays.Rune import Rune

engine = InitDB('sqlite://')
#engine = create_engine('sqlite:///:memory:', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

file_limit = 100

json_files = list(Path('./tests/Data/').glob('*.json'))


def test_add():
    for j in json_files[:file_limit]:
        print(j)
        populate_from_JSON_file(j, session)
    
    session.commit()


test_add()


def test_update():
    for j in json_files[:file_limit]:
        print(j)
        populate_from_JSON_file(j, session, skip_existing=False)

    session.commit()


tables = [
          Replay,
          Player,
          Smoke,
          TeamSelections,
          Ward,
          Scan,
          Rune,
          Kills,
          Deaths,
          Denies,
          Assists,
         ]


def count_all_instances(filt=None):
    query = lambda x: session.query(x) if filt is None\
            else lambda x: session.query(x).filter(filt)

    for t in tables:
        print(t, query(t).count())


def test_delete():
    replay = session.query(Replay).first()
    session.delete(replay)

    session.commit()