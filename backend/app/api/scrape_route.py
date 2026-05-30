from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services.transcript import TranscriptRequest, extract_transcript
from ..services.scraper import extract_metadata, ScrapeRequest

router = APIRouter(prefix="/scraper", tags=["scraper"])


def _resolve_cookie_path(url_host: str) -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    host = url_host.lower()

    if "instagram.com" in host:
        return backend_root / "instagram_cookies.txt"

    if host.endswith("youtube.com") or host == "youtu.be":
        return backend_root / "youtube_cookies.txt"

    return backend_root / "cookies.txt"


@router.post("/transcript")
def get_transcript(payload: TranscriptRequest) -> Dict[str, Any]:
    cookies_path = _resolve_cookie_path(payload.url.host)

    if not cookies_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"{cookies_path.name} not found",
        )

    try:
        return extract_transcript(
            payload,
            cookiefile=str(cookies_path),
        ).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    

@router.post("/")
def scrape_media(payload: ScrapeRequest) -> Dict[str, Any]:
    cookies_path = _resolve_cookie_path(payload.url.host)

    if not cookies_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"{cookies_path.name} not found",
        )

    return extract_metadata(
        payload,
        cookiefile=str(cookies_path),
    )