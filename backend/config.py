import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

NORAD_ID = int(os.environ.get("KNACKSAT2_NORAD_ID", "67683"))
SATYAML_PATH = Path(
    os.environ.get("KNACKSAT2_SATYAML", str(PROJECT_ROOT / "satyaml" / "KNACKSAT-2.yml"))
)

SATNOGS_API_BASE = os.environ.get("SATNOGS_API_BASE", "https://network.satnogs.org/api")

GR_SATELLITES_BIN = os.environ.get("GR_SATELLITES_BIN", "gr_satellites")
GR_SATELLITES_EXTRA_ARGS = os.environ.get("GR_SATELLITES_EXTRA_ARGS", "").split()
GR_SATELLITES_TIMEOUT_SEC = int(os.environ.get("GR_SATELLITES_TIMEOUT_SEC", "600"))

DATA_DIR = Path(os.environ.get("KNACKSAT2_DATA_DIR", str(PROJECT_ROOT / "data")))
AUDIO_DIR = DATA_DIR / "audio"
RESULTS_DIR = DATA_DIR / "results"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
