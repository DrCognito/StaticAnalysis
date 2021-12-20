import pathlib
from dotenv import load_dotenv
from os import environ as environment
import pygsheets
import json

load_dotenv(dotenv_path="setup.env")
SCRIMS_PATH = environment['SCRIMS_DIR']
SCRIMS_JSON_PATH = environment['SCRIMS_JSON']

scrims_dir = pathlib.Path(SCRIMS_PATH)
scrims = list(scrims_dir.glob('*.dem'))

# with open('scrims.txt', 'a') as f:
#     for s in scrims:
#         print(f"Adding {s.stem}.")
#         f.write(f"{s.stem}\n")


gc = pygsheets.authorize(outh_file="client_secret_1032893103395-vtiha2lmocsru6nvc96ipnrjj10lue23.apps.googleusercontent.com.json")
# Test sheet
# sheet = gc.open_by_key('1vZOk0Gx9Wzf45zxnNP8FmOBiXTsYXdyJ7xXE_V60A2o')
# Real sheet
sheet = gc.open_by_key('1HbH7GShRz7-kuVVlMaehmSm_AXBSCvGwmYuDYvLfhpA')

scrim_sheet = sheet.worksheet_by_title(r"Past Scrim ID's")
# Column uses numbers, starting at 1! returns list[string]
team_names = scrim_sheet.get_col(2)
scrim_ids = scrim_sheet.get_col(3)

if len(team_names) != len(scrim_ids):
    print("Warning: team names do not match scrim ids in length!")
scrim_dict = {}

for scrim_id, name in zip(scrim_ids[2:], team_names[2:]):
    if scrim_id == '':
        # Lots of trailing info in the columns.
        break
    scrim_dict[int(scrim_id)] = name


with open(SCRIMS_JSON_PATH, 'w') as f:
    json.dump(scrim_dict, f)

