from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field, HttpUrl
from dotenv import load_dotenv
import os
import yt_dlp

load_dotenv()

WISPER_MODEL = os.getenv("WISPER_MODEL") or ""

class TranscriptRequest(BaseModel):
	url: HttpUrl
	language: str | None = Field(default=None)


class TranscriptSegment(BaseModel):
	text: str
	start: float
	duration: float


class TranscriptResponse(BaseModel):
	source: Literal["youtube", "instagram"]
	method: str
	url: HttpUrl
	title: str | None = None
	video_id: str | None = None
	language: str | None = None
	transcript: str
	segments: list[TranscriptSegment] = Field(default_factory=list)
	metadata: dict[str, Any] = Field(default_factory=dict)


def _host(url: HttpUrl) -> str:
	return (url.host or "").lower()


def _is_youtube_host(host: str) -> bool:
	return "youtube.com" in host or host == "youtu.be"


def _is_instagram_host(host: str) -> bool:
	return "instagram.com" in host


def _extract_youtube_video_id(url: str) -> str:
	parsed_url = urlparse(url)
	hostname = parsed_url.netloc.lower()

	if hostname == "youtu.be":
		video_id = parsed_url.path.lstrip("/")
		if video_id:
			return video_id

	query_values = parse_qs(parsed_url.query)
	if query_values.get("v"):
		return query_values["v"][0]

	path_parts = [part for part in parsed_url.path.split("/") if part]
	for marker in ("shorts", "embed", "live"):
		if marker in path_parts:
			marker_index = path_parts.index(marker)
			if marker_index + 1 < len(path_parts):
				return path_parts[marker_index + 1]

	raise ValueError("Could not determine the YouTube video id from the URL")


def _get_youtube_transcript(video_id: str, language: str | None = None) -> tuple[list[TranscriptSegment], str]:
	try:
		youtube_transcript_api = importlib.import_module("youtube_transcript_api")
	except ModuleNotFoundError as exc:
		raise RuntimeError("youtube-transcript-api is required to extract YouTube transcripts") from exc

	YouTubeTranscriptApi = youtube_transcript_api.YouTubeTranscriptApi
	api = YouTubeTranscriptApi()
	transcript_list = api.list(video_id)
	preferred_languages = [language] if language else ["en"]

	try:
		transcript = transcript_list.find_transcript(preferred_languages)
	except Exception:
		generated_transcripts = getattr(transcript_list, "_generated_transcripts", {}) or {}
		manual_transcripts = getattr(transcript_list, "_manually_created_transcripts", {}) or {}
		transcript = next(iter(manual_transcripts.values()), None) or next(iter(generated_transcripts.values()), None)
		if transcript is None:
			raise RuntimeError(f"No transcript is available for video {video_id}")

	transcript_data = transcript.fetch().to_raw_data()

	segments = [
		TranscriptSegment(
			text=segment["text"],
			start=float(segment["start"]),
			duration=float(segment["duration"]),
		)
		for segment in transcript_data
		if segment.get("text")
	]
	transcript_text = "\n".join(segment.text.strip() for segment in segments if segment.text.strip())
	return segments, transcript_text


@lru_cache(maxsize=4)
def _load_whisper_model(model_name: str):
	try:
		whisper = importlib.import_module("whisper")
	except ModuleNotFoundError as exc:
		raise RuntimeError("openai-whisper is required to transcribe Instagram audio") from exc

	return whisper.load_model(model_name)


def _download_instagram_audio(temp_path: Path, url: str, cookiefile: str | None = None) -> tuple[Path, dict[str, Any]]:
	ydl_opts = {
		"quiet": True,
		"no_warnings": True,
		"noplaylist": True,
		"format": "bestaudio/best",
		"outtmpl": str(temp_path / "%(id)s.%(ext)s"),
	}

	if cookiefile:
		ydl_opts["cookiefile"] = cookiefile

	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=True)
		audio_path = Path(ydl.prepare_filename(info))

	if not audio_path.exists():
		candidates = sorted(temp_path.glob(f"{info.get('id', '*')}.*"))
		if not candidates:
			raise FileNotFoundError("Failed to download Instagram audio")
		audio_path = candidates[0]

	return audio_path


def _transcribe_instagram_audio(audio_path: Path, language: str | None = None) -> tuple[list[TranscriptSegment], str]:
	model = _load_whisper_model(WISPER_MODEL)
	result = model.transcribe(str(audio_path), fp16=False, language=language)

	raw_segments = result.get("segments", [])
	segments = [
		TranscriptSegment(
			text=segment.get("text", "").strip(),
			start=float(segment.get("start", 0.0)),
			duration=float(segment.get("duration", 0.0)),
		)
		for segment in raw_segments
		if segment.get("text")
	]
	transcript_text = result.get("text", "").strip()
	if not transcript_text:
		transcript_text = "\n".join(segment.text for segment in segments if segment.text)

	return segments, transcript_text


def extract_transcript(payload: TranscriptRequest, cookiefile: str | None = None) -> TranscriptResponse:
	host = _host(payload.url)
	url = str(payload.url)

	if _is_youtube_host(host):
		video_id = _extract_youtube_video_id(url)
		segments, transcript_text = _get_youtube_transcript(video_id, payload.language)

		return TranscriptResponse(
			source="youtube",
			method="youtube_transcript_api",
			url=payload.url,
			video_id=video_id,
			language=payload.language,
			transcript=transcript_text,
			segments=segments,
		)

	if _is_instagram_host(host):
		with TemporaryDirectory() as temp_dir:
			temp_path = Path(temp_dir)
			audio_path= _download_instagram_audio(temp_path, url, cookiefile=cookiefile)
			try:
				segments, transcript_text = _transcribe_instagram_audio(audio_path, payload.language)
			finally:
				if audio_path.exists():
					audio_path.unlink(missing_ok=True)

		return TranscriptResponse(
			source="instagram",
			method="whisper_asr",
			url=payload.url,
			language=payload.language,
			transcript=transcript_text,
			segments=segments,
		)

	raise ValueError("Unsupported URL host. Only YouTube and Instagram URLs are supported.")
