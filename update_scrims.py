import pathlib
from dotenv import load_dotenv
from os import environ as environment

load_dotenv(dotenv_path="setup.env")
SCRIMS_PATH = environment['SCRIMS_DIR']

scrims_dir = pathlib.Path(SCRIMS_PATH)
scrims = list(scrims_dir.glob('*.dem'))

with open('scrims.txt', 'a') as f:
    for s in scrims:
        print(f"Adding {s.stem}.")
        f.write(f"{s.stem}\n")
