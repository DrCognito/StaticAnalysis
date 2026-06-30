from StaticAnalysis import CONFIG
from pathlib import Path
import json

global_path = Path(CONFIG['output']['SUMMARY_PLOT_PATH']) / "global_plots.json"

with open(global_path, 'r') as f:
    global_json = json.load(f)