import logging.handlers
from sqlalchemy.orm import sessionmaker
from propubs.model.pub_heroes import InitDB as InitPubDB
from StaticAnalysis.lib.team_info import InitTeamDB
from StaticAnalysis.replays.Replay import InitDB
from pathlib import Path
import tomllib
from PIL import ImageFont
from loguru import logger as LOG
from sys import stdout
from tqdm import tqdm

import logging
import inspect
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = LOG.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        LOG.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# logging.basicConfig()
# sql_log = logging.getLogger("sqlalchemy.engine")
# sql_log.setLevel(logging.INFO)
# sql_log.propagate = False
# sql_log.addHandler(InterceptHandler())

LOG.remove()
LOG.add(lambda msg: tqdm.write(msg, end=""), format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> <level>{level}</level> {message}", colorize=True, level='INFO')
LOG.add("app.log", rotation="5 MB", level='DEBUG', retention=0)

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