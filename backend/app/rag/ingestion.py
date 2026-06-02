from typing import Any, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..model.transcript_model import TranscriptResponse
import logging

logging.basicConfig(level=logging.INFO)


def _sanitize_metadata(md: Dict[str, Any]) -> Dict[str, Any]:
    """Convert metadata into Pinecone-safe scalar values or list[str]."""
    safe: Dict[str, Any] = {}
    for key, value in (md or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = [str(item) for item in value]
        else:
            safe[key] = str(value)
    return safe

def _safe_num(value, default=0):
    try:
        return 0 if value is None else float(value)
    except Exception:
        return default


def _chunk_and_store_transcript(INDEX,NAMESPACE,metadatas, ids: list, video_id: str, source: str, metadata: Dict, transcript: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
    transcript = transcript or ""
    if not transcript.strip():
        fallback = (metadata.get("description") or "")
        if not fallback.strip():
            fallback = (metadata.get("title") or "")
        transcript = fallback or transcript
    size = len(transcript)

    if chunk_size is None:
        chunk_size = max(256, size // 5) if size > 0 else 1000
    else:
        chunk_size = int(chunk_size)

    if overlap is None:
        overlap = max(64, (chunk_size * 2) // 5)
    else:
        overlap = int(overlap)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, length_function=len)
    document_chunks = text_splitter.split_text(transcript)
    records = []

    like = _safe_num(metadata.get("like_count", 0))
    comment = _safe_num(metadata.get("comment_count", 0))
    view = _safe_num(metadata.get("view_count", 0))
    duration = _safe_num(metadata.get("duration", 0))

    engagement_rate = (like + comment) * 100.0 / view if view else 0.0


    controversy = 0.0
    denom = (comment + like)
    if denom:
        controversy = comment / denom

    raw_metadata = {
        "video_id": str(video_id),
        "engagement_rate": engagement_rate,
        "like_rate": (like / view) if view else 0.0,
        "comment_rate": (comment / view) if view else 0.0,
        "controvercy_score": controversy,
        "engagement_per_second": ((like + comment) / duration) if duration else 0.0,
        "interaction_per_1000_views": engagement_rate * 10,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "uploader": metadata.get("uploader"),
        "channel": metadata.get("channel"),
        "duration": duration,
        "view_count": int(view),
        "like_count": int(like),
        "comment_count": int(comment),
        "thumbnail": metadata.get("thumbnail"),
    }

    safe_metadata = _sanitize_metadata(raw_metadata)
    metadatas[video_id] = safe_metadata

    local_ids = []
    for idx, chunk_text in enumerate(document_chunks):
        rec_id = f"{video_id}_{idx}"
        record = {
            "id": rec_id,
            "video_id": str(video_id),
            "text": chunk_text,
        }
        # record.update(safe_metadata)
        records.append(record)
        local_ids.append(rec_id)
    ids.extend(local_ids)
    

    if not INDEX:
        logging.warning("Pinecone index not configured; skipping upsert.")
        return {"chunks_stored": len(records), "metadata_stored": False, "video_id": video_id}

    try:
        INDEX.upsert_records(namespace=NAMESPACE, records=records)
        logging.info("Upserted %d records for video %s", len(records), video_id)
        return {"chunks_stored": len(records), "metadata_stored": True, "video_id": video_id}
    except Exception as e:
        logging.exception("Failed to upsert records to Pinecone: %s", e)
        return {"chunks_stored": 0, "metadata_stored": False, "error": str(e)}


def _normalize_transcript_payload(payload: TranscriptResponse | Dict[str, Any]):
    if isinstance(payload, dict):
        return payload

    return {
        "source": payload.source,
        "transcript": payload.transcript,
        "metadata": payload.metadata or {},
        "video_id": payload.video_id,
    }


def chunk_and_store(INDEX,NAMESPACE,metadatas,ids,payload: TranscriptResponse | Dict[str, Any]):
    normalized_payload = _normalize_transcript_payload(payload)
    transcript = normalized_payload.get("transcript") or ""
    metadata = normalized_payload.get("metadata") or {}
    size = len(transcript)

    chunk_size = max(256, size // 5) if size > 0 else 1000
    overlap = max(64, (chunk_size * 2) // 5)

    video_id = metadata.get("id") or normalized_payload.get("video_id") or normalized_payload.get("source") or "unknown"
    source = normalized_payload.get("source") or "unknown"

    return _chunk_and_store_transcript(
        INDEX,
        NAMESPACE,
        metadatas,
        ids,
        video_id,
        source,
        metadata,
        transcript,
        chunk_size=chunk_size,
        overlap=overlap,
    )



