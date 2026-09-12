"""Thin client for the public SatNOGS Network API (read-only)."""
import httpx

from config import NORAD_ID, SATNOGS_API_BASE


async def list_observations(
    status: str | None = "good",
    start: str | None = None,
    end: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Fetch KNACKSAT-2 observations from the public SatNOGS Network API.

    Only metadata is returned here; audio is downloaded separately, on demand,
    when a decode is requested.
    """
    params = {"norad_cat_id": NORAD_ID, "format": "json"}
    if status:
        params["status"] = status
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{SATNOGS_API_BASE}/observations/", params=params)
        resp.raise_for_status()
        observations = resp.json()

    observations = observations[:limit]
    return [_simplify(obs) for obs in observations]


async def get_observation(observation_id: int) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{SATNOGS_API_BASE}/observations/{observation_id}/",
            params={"format": "json"},
        )
        resp.raise_for_status()
        return resp.json()


async def download_audio(url: str, dest_path) -> None:
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)


def _simplify(obs: dict) -> dict:
    return {
        "id": obs.get("id"),
        "start": obs.get("start"),
        "end": obs.get("end"),
        "status": obs.get("status"),
        "station_name": obs.get("station_name"),
        "station_lat": obs.get("station_lat"),
        "station_lng": obs.get("station_lng"),
        "transmitter_mode": obs.get("transmitter_mode"),
        "transmitter_description": obs.get("transmitter_description"),
        "transmitter_baud": obs.get("transmitter_baud"),
        "observation_frequency": obs.get("observation_frequency"),
        "payload": obs.get("payload"),
        "waterfall": obs.get("waterfall"),
        "has_audio": bool(obs.get("payload")),
    }
