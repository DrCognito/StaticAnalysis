import logging.handlers
from sqlalchemy.orm import sessionmaker
from propubs.model.pub_heroes import InitDB as InitPubDB
from StaticAnalysis.lib.team_info import InitTeamDB
from StaticAnalysis.replays.Replay import InitDB
from pathlib import Path
import tomllib
from PIL import ImageFont
import logging

LOG = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel("INFO")
file_handler = logging.handlers.RotatingFileHandler(
    "app.log", mode="a", encoding="utf-8",
    maxBytes=5000000, backupCount=0)
file_handler.setLevel("DEBUG")
LOG.addHandler(console_handler)
LOG.addHandler(file_handler)

config_path = Path('setup.toml')
try:
    with open(config_path, 'rb') as f:
        CONFIG = tomllib.load(f)
except FileNotFoundError:
    LOG.error("Failed to load toml config file.")
    LOG.error(f"Expected path is {config_path.resolve()}")
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