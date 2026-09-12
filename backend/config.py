import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

NORAD_ID = int(os.environ.get("KNACKSAT2_NORAD_ID", "67683"))
SATYAML_PATH = Path(
    os.environ.get("KNACKSAT2_SATYAML", str(PROJECT_ROOT / "satyaml" / "KNACKSAT-2.yml"))
)

SATNOGS_API_BASE = os.environ.get("SATNOGS_API_BASE", "https://network.satnogs.org/api")

# gr-satellites needs a real GNU Radio install. If GR_SATELLITES_CONDA_ENV isn't
# set explicitly, fall back to this machine's existing "sdr" conda env (has
# gnuradio + gnuradio-satellites already installed) when present, so the app
# works out of the box here without requiring `conda activate` first. On a
# machine without that env, GR_SATELLITES_BIN/GR_SATELLITES_CONDA_ENV should be
# set explicitly (or `conda activate` the env before running uvicorn).
_DEFAULT_CONDA_ENV = Path(os.environ.get("USERPROFILE", "")) / "miniconda3" / "envs" / "sdr"
GR_SATELLITES_CONDA_ENV = Path(
    os.environ.get("GR_SATELLITES_CONDA_ENV", str(_DEFAULT_CONDA_ENV))
)
_default_bin = GR_SATELLITES_CONDA_ENV / "Library" / "bin" / "gr_satellites.exe"
GR_SATELLITES_BIN = os.environ.get(
    "GR_SATELLITES_BIN", str(_default_bin) if _default_bin.exists() else "gr_satellites"
)
GR_SATELLITES_EXTRA_ARGS = os.environ.get("GR_SATELLITES_EXTRA_ARGS", "").split()
GR_SATELLITES_TIMEOUT_SEC = int(os.environ.get("GR_SATELLITES_TIMEOUT_SEC", "600"))


def _build_subprocess_env() -> dict:
    """PATH gr_satellites.exe needs to find its own DLL/runtime dependencies.

    Conda env executables on Windows aren't self-contained: without the env's
    own directories on PATH (normally added by `conda activate`), the process
    launches but fails with ModuleNotFoundError for `gnuradio` even though the
    exe itself is found fine.
    """
    env = dict(os.environ)
    if GR_SATELLITES_CONDA_ENV.exists():
        extra_dirs = [
            str(GR_SATELLITES_CONDA_ENV),
            str(GR_SATELLITES_CONDA_ENV / "Library" / "mingw-w64" / "bin"),
            str(GR_SATELLITES_CONDA_ENV / "Library" / "usr" / "bin"),
            str(GR_SATELLITES_CONDA_ENV / "Library" / "bin"),
            str(GR_SATELLITES_CONDA_ENV / "Scripts"),
            str(GR_SATELLITES_CONDA_ENV / "bin"),
        ]
        env["PATH"] = os.pathsep.join(extra_dirs) + os.pathsep + env.get("PATH", "")
    return env


GR_SATELLITES_ENV = _build_subprocess_env()

DATA_DIR = Path(os.environ.get("KNACKSAT2_DATA_DIR", str(PROJECT_ROOT / "data")))
AUDIO_DIR = DATA_DIR / "audio"
RESULTS_DIR = DATA_DIR / "results"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
