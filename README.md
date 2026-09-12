# KNACKSAT-2 Decoder

A small web app that pulls recorded passes of **KNACKSAT-2** (NORAD 67683,
Thailand's HS0K CubeSat) from the public [SatNOGS Network](https://network.satnogs.org)
API and decodes the FSK9600 / AX.25 (G3RUH-scrambled) telemetry using
[gr-satellites](https://github.com/daniestevez/gr-satellites) on top of GNU Radio.

KNACKSAT-2 has two 9k6 FSK/AX.25-G3RUH transmitters:
- UHF telemetry downlink: 400.630 MHz
- VHF digipeater: 145.825 MHz

Both are described in [`satyaml/KNACKSAT-2.yml`](satyaml/KNACKSAT-2.yml), a custom
gr-satellites satellite definition (KNACKSAT-2 isn't in gr-satellites' built-in list,
but the format is the same one used for dozens of other 9k6 AX.25 G3RUH cubesats).
Telemetry field-level parsing (temperatures, battery voltage, etc.) is **not**
implemented — SatNOGS DB has its own decoder for that (`knacksat2` in
[satnogs-decoders](https://gitlab.com/librespacefoundation/satnogs/satnogs-decoders)),
which would be the reference to port if you want structured telemetry instead of
raw AX.25 frame hex/ASCII.

## Architecture

```
frontend/  static HTML/JS UI (served by FastAPI)
backend/
  main.py           FastAPI app + routes
  satnogs_client.py SatNOGS Network API client (list observations, download audio)
  decoder.py        runs `gr_satellites` as a subprocess against the audio file
  ax25.py           pure-Python KISS/AX.25 frame parser (no extra deps)
  jobs.py           in-memory async job tracker (decoding runs in the background)
satyaml/KNACKSAT-2.yml   gr-satellites satellite definition
data/audio/, data/results/  downloaded recordings + decode output (gitignored)
```

Flow: browse observations → pick one → backend downloads its `.ogg` recording
from SatNOGS → runs `gr_satellites` against it (gr-satellites reads WAV/OGG/FLAC
directly, no conversion step needed) → KISS output is parsed into AX.25 frames →
frontend polls the job and renders the frame table.

## Setup

GNU Radio + gr-satellites are the only non-trivial dependencies, and the
easiest way to get both on Windows is conda:

```powershell
conda env create -f environment.yml
conda activate knacksat2-decoder
```

This installs GNU Radio, gr-satellites, and the Python web dependencies
(FastAPI, uvicorn, httpx) all into one environment. If you already manage
GNU Radio separately (e.g. via an existing conda/mamba env), just add
`gnuradio-satellites` to it and `pip install -r backend/requirements.txt`.

Verify gr-satellites is on PATH:

```powershell
gr_satellites --list_satellites
```

**Note for this machine:** it already has a working `sdr` conda env at
`C:\Users\<you>\miniconda3\envs\sdr` with `gnuradio` + `gnuradio-satellites`
installed — `environment.yml` above doesn't need to be run here.
`backend/config.py` auto-detects that env (via `GR_SATELLITES_CONDA_ENV`,
defaulting to `~\miniconda3\envs\sdr`) and points `GR_SATELLITES_BIN` at
`<env>\Library\bin\gr_satellites.exe` directly, and prepends that env's
`Library\bin`/`Scripts`/etc. directories to `PATH` for the subprocess (a
plain conda env executable isn't self-contained on Windows — without those
directories on `PATH`, the DLL/`gnuradio` module isn't found even though the
`.exe` runs). Only the lightweight web dependencies (FastAPI/uvicorn/httpx,
in `.venv/`) need to be installed separately to run the FastAPI process
itself; it just shells out to the conda env's `gr_satellites.exe` for the
actual decode.

## Run

```powershell
conda activate knacksat2-decoder
cd backend
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000

## Configuration (environment variables, all optional)

| Variable | Default | Purpose |
|---|---|---|
| `KNACKSAT2_NORAD_ID` | `67683` | NORAD ID used to query SatNOGS |
| `KNACKSAT2_SATYAML` | `satyaml/KNACKSAT-2.yml` | satellite definition passed to gr_satellites |
| `GR_SATELLITES_CONDA_ENV` | `~\miniconda3\envs\sdr` | conda env root to source `gr_satellites.exe` and its `PATH` from, if it exists |
| `GR_SATELLITES_BIN` | auto-detected exe in `GR_SATELLITES_CONDA_ENV`, else `gr_satellites` | explicit override for the executable path |
| `GR_SATELLITES_EXTRA_ARGS` | *(empty)* | extra space-separated CLI flags, e.g. tuning `--f_offset` |
| `GR_SATELLITES_TIMEOUT_SEC` | `600` | kill the decode subprocess after this long |
| `KNACKSAT2_DATA_DIR` | `./data` | where downloaded audio + decode results are cached |

## Notes / caveats

- The 400.630 MHz UHF telemetry downlink is outside the amateur allocation —
  this tool is receive-only (downloads existing public SatNOGS recordings and
  decodes them locally); it never transmits.
- Default demodulator parameters work fine as-is: confirmed against real
  KNACKSAT-2 "good" observations (3 of 5 tested decoded real AX.25 frames,
  e.g. dest `HS0AK-11` / src `HS0K-0`, info ending in `BCN`) and cross-checked
  against gr-satellites' own official FSK9k6/AX.25-G3RUH reference recording
  (US01). A zero-frame result for a specific pass is normal and expected —
  SatNOGS "good" status reflects a human's visual read of the waterfall, not
  a guarantee that the signal was strong enough to fully deframe.
- Only a handful of observations exist for a newly-deployed satellite; widen
  the status filter to "any" in the UI if "good" returns nothing yet.
