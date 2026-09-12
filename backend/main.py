import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import satnogs_client
from config import PROJECT_ROOT
from decoder import audio_path_for, run_gr_satellites
import jobs

app = FastAPI(title="KNACKSAT-2 Decoder")

FRONTEND_DIR = PROJECT_ROOT / "frontend"


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/observations")
async def observations(status: str = "good", start: str | None = None, end: str | None = None, limit: int = 25):
    try:
        return await satnogs_client.list_observations(status=status, start=start, end=end, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"SatNOGS API error: {exc}") from exc


@app.post("/api/decode/{observation_id}")
async def decode(observation_id: int):
    obs = await satnogs_client.get_observation(observation_id)
    payload_url = obs.get("payload")
    if not payload_url:
        raise HTTPException(status_code=400, detail="This observation has no recorded audio (payload is empty).")

    audio_path = audio_path_for(observation_id, payload_url)
    if not audio_path.exists():
        await satnogs_client.download_audio(payload_url, audio_path)

    job_id = jobs.create_job(observation_id)

    async def _task():
        return await run_gr_satellites(observation_id, audio_path)

    asyncio.create_task(jobs.run_job(job_id, _task))
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: int):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return job


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
