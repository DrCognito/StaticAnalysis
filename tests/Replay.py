import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from replays.Replay import populate_from_JSON_file, InitDB
from pathlib import Path
from sqlalchemy.orm import sessionmaker

engine = InitDB('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()

json_files = list(Path('./tests/Data/').glob('*.json'))
for j in json_files:
    print(j)
    populate_from_JSON_file(j, session)
