"""Runs gr-satellites (GNU Radio) against a downloaded observation audio file."""
import asyncio
import time
from pathlib import Path

from config import (
    AUDIO_DIR,
    GR_SATELLITES_BIN,
    GR_SATELLITES_ENV,
    GR_SATELLITES_EXTRA_ARGS,
    GR_SATELLITES_TIMEOUT_SEC,
    RESULTS_DIR,
    SATYAML_PATH,
)
from ax25 import parse_kiss_file


class DecodeError(Exception):
    pass


def audio_path_for(observation_id: int, source_url: str) -> Path:
    suffix = Path(source_url).suffix or ".ogg"
    return AUDIO_DIR / f"obs_{observation_id}{suffix}"


async def run_gr_satellites(observation_id: int, audio_path: Path) -> dict:
    """Runs `gr_satellites KNACKSAT-2.yml --wavfile <audio> --kiss_out <kiss>`.

    gr-satellites reads WAV/OGG/FLAC directly via libsndfile, so no audio
    conversion step is needed before handing it the recording.
    """
    kiss_path = RESULTS_DIR / f"obs_{observation_id}.kiss"
    log_path = RESULTS_DIR / f"obs_{observation_id}.log"
    kiss_path.unlink(missing_ok=True)

    cmd = [
        GR_SATELLITES_BIN,
        str(SATYAML_PATH),
        "--wavfile",
        str(audio_path),
        "--kiss_out",
        str(kiss_path),
        "--hexdump",
        *GR_SATELLITES_EXTRA_ARGS,
    ]

    started = time.time()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=GR_SATELLITES_ENV,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=GR_SATELLITES_TIMEOUT_SEC)
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise DecodeError(
            f"gr_satellites timed out after {GR_SATELLITES_TIMEOUT_SEC}s"
        ) from exc

    log_path.write_bytes(stdout)
    duration = time.time() - started

    if proc.returncode != 0:
        raise DecodeError(
            f"gr_satellites exited with code {proc.returncode}. "
            f"See log: {log_path}\n--- tail of output ---\n"
            + stdout.decode(errors="replace")[-2000:]
        )

    frames = parse_kiss_file(kiss_path) if kiss_path.exists() else []

    return {
        "observation_id": observation_id,
        "command": " ".join(cmd),
        "duration_sec": round(duration, 1),
        "frame_count": len(frames),
        "frames": frames,
        "log_tail": stdout.decode(errors="replace")[-4000:],
    }
