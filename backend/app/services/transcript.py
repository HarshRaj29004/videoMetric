from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse
from deepgram import DeepgramClient
from .metadata import extract_metadata, MetadataRequest
from ..model.transcript_model import TranscriptRequest,TranscriptResponse,TranscriptSegment


from dotenv import load_dotenv
import os
import yt_dlp

load_dotenv()

WISPER_MODEL = os.getenv("WISPER_MODEL") or "tiny"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
TRANSCRIPT_SEGMENT_COUNT = int(os.getenv("TRANSCRIPT_SEGMENT_COUNT") or "10")


def _is_youtube_host(host: str) -> bool:
	return "youtube.com" in host or host == "youtu.be"


def _is_instagram_host(host: str) -> bool:
	return "instagram.com" in host


def _group_segments_into_time_buckets(segments: list[TranscriptSegment], bucket_count: int = TRANSCRIPT_SEGMENT_COUNT) -> tuple[list[TranscriptSegment], str, dict[str, Any]]:
	if not segments:
		return [], "", {"truncated": False, "bucket_count": bucket_count}

	total_duration = max((segment.start + segment.duration) for segment in segments)
	if total_duration <= 0:
		joined_text = " ".join(segment.text for segment in segments if segment.text)
		return [TranscriptSegment(text=joined_text, start=0.0, duration=0.0)], {
			"truncated": False,
			"bucket_count": 1,
		}
	
	bucket_duration = total_duration / bucket_count
	buckets: list[TranscriptSegment] = []

	for bucket_index in range(bucket_count):
		bucket_start = bucket_index * bucket_duration
		bucket_end = total_duration if bucket_index == bucket_count - 1 else (bucket_index + 1) * bucket_duration
		bucket_segments = [
			segment
			for segment in segments
			if bucket_start <= segment.start < bucket_end or (bucket_index == bucket_count - 1 and segment.start + segment.duration >= bucket_start)
		]
		bucket_text = " ".join(segment.text.strip() for segment in bucket_segments if segment.text.strip()).strip()
		if not bucket_text and bucket_segments:
			bucket_text = " ".join(segment.text.strip() for segment in bucket_segments[:3] if segment.text.strip()).strip()
		if not bucket_text:
			continue

		buckets.append(
			TranscriptSegment(
				text=bucket_text,
				start=round(bucket_start, 2),
				duration=round(bucket_end - bucket_start, 2),
			)
		)

	return buckets


def _get_youtube_transcript(video_id: str, language: str | None = None, cookiefile: str | None = None) -> tuple[list[TranscriptSegment], str]:
	try:
		youtube_transcript_api = importlib.import_module("youtube_transcript_api")
	except ModuleNotFoundError as exc:
		raise RuntimeError("youtube-transcript-api is required to extract YouTube transcripts") from exc

	YouTubeTranscriptApi = youtube_transcript_api.YouTubeTranscriptApi

	http_client = None
	if cookiefile:
		import requests
		import http.cookiejar
		session = requests.Session()
		try:
			cj = http.cookiejar.MozillaCookieJar(cookiefile)
			cj.load(ignore_discard=True, ignore_expires=True)
			session.cookies = cj
			http_client = session
		except Exception as e:
			print(f"Failed to load cookies into youtube-transcript-api: {str(e)}")

	api = YouTubeTranscriptApi(http_client=http_client)
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
	deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
	with audio_path.open("rb") as audio_file:
		result = deepgram.listen.v1.media.transcribe_file(
			request=audio_file.read(),
			model="nova-3",
			language=language or "en",
			smart_format=True,
		)

	channels = getattr(result.results, "channels", []) if getattr(result, "results", None) else []
	alternatives = channels[0].alternatives if channels else []
	primary_alternative = alternatives[0] if alternatives else None
	words = getattr(primary_alternative, "words", []) if primary_alternative else []
	raw_segments = [word for word in words if (getattr(word, "word", None) if not isinstance(word, dict) else word.get("word"))]
	segments = [
		TranscriptSegment(
			text=((getattr(segment, "word", None) if not isinstance(segment, dict) else segment.get("word", "")) or "").strip(),
			start=float(getattr(segment, "start", 0.0) if not isinstance(segment, dict) else segment.get("start", 0.0)),
			duration=float(getattr(segment, "duration", 0.0) if not isinstance(segment, dict) else segment.get("duration", 0.0)),
		)
		for segment in raw_segments
		if (getattr(segment, "word", None) if not isinstance(segment, dict) else segment.get("word"))
	]

	transcript_text = ""
	if primary_alternative is not None:
		transcript_text = getattr(primary_alternative, "transcript", "") or ""
		if isinstance(primary_alternative, dict):
			transcript_text = primary_alternative.get("transcript", "") or ""
	transcript_text = transcript_text.strip()
	if not transcript_text:
		transcript_text = "\n".join(segment.text for segment in segments if segment.text)

	return segments, transcript_text


def extract_transcript(payload: TranscriptRequest, cookiefile: str | None = None) -> TranscriptResponse:
	host = urlparse(str(payload.url)).netloc.lower()
	url = str(payload.url)
	metadata = extract_metadata(MetadataRequest(url=url), cookiefile)

	if _is_youtube_host(host):
		video_id = metadata.get("id")
		segments, transcript_text = _get_youtube_transcript(video_id, payload.language, cookiefile)
		segments = _group_segments_into_time_buckets(segments)

		return TranscriptResponse(
			source="youtube",
			method="youtube_transcript_api",
			url=payload.url,
			video_id=video_id,
			language=payload.language,
			transcript=transcript_text,
			segments=segments,
			metadata=metadata,
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
			segments = _group_segments_into_time_buckets(segments)

		return TranscriptResponse(
			source="instagram",
			method="whisper_asr",
			url=payload.url,
			language=payload.language,
			transcript=transcript_text,
			segments=segments,
			metadata=metadata,
		)

	raise ValueError("Unsupported URL host. Only YouTube and Instagram URLs are supported.")
