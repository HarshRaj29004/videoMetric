from typing import Any, Dict, Optional

from pydantic import BaseModel, HttpUrl
import yt_dlp


class ScrapeRequest(BaseModel): 
     url: HttpUrl

def extract_metadata(url: ScrapeRequest, cookiefile: Optional[str] = None) -> Dict[str, Any]:

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
    }

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(str(url.url), download=False, process=False)

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader"),
        "channel": info.get("channel"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "thumbnail": info.get("thumbnail"),
        "url": info.get("webpage_url"),
        "webpage_url": info.get("webpage_url"),
        "extractor": info.get("extractor"),
    }
