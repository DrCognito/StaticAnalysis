from sqlalchemy.orm import sessionmaker
from propubs.model.pub_heroes import InitDB as InitPubDB
from StaticAnalysis.lib.team_info import InitTeamDB
from StaticAnalysis.replays.Replay import InitDB
from pathlib import Path
import tomllib
from collections import defaultdict
from PIL import ImageFont

config_path = Path('setup.toml')
try:
    with open(config_path, 'rb') as f:
        CONFIG = tomllib.load(f)
except FileNotFoundError:
    print("Failed to load toml config file.")
    print(f"Expected path is {config_path.resolve()}")
    exit

DB_PATH = CONFIG['database']['PARSED_DB_PATH']
PLOT_BASE_PATH = CONFIG['output']['PLOT_OUTPUT']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

team_engine = InitTeamDB()
team_maker = sessionmaker(bind=team_engine)
team_session = team_maker()

pub_engine = InitPubDB()
pub_maker = sessionmaker(bind=pub_engine)
pub_session = pub_maker()

# https://stackoverflow.com/questions/71689286/any-workaround-to-pass-multiple-arguments-to-defaultdicts-default-factory
class CacheDict(dict):
    def __init__(self, factory: callable):
        self.factory = factory
    def __missing__(self, key):
        if self.factory is None:
            raise KeyError(key)
        
        value = self.factory(key)
        self[key] = value
        return value

FONT_CACHE = CacheDict(lambda x: ImageFont.truetype(x[0], x[1]))