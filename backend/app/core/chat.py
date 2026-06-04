from typing import Any, Dict
from urllib.parse import urlparse
from pathlib import Path

from .data_extraction import _resolve_cookie_path
from ..rag.delete import reset_vector_db
from ..rag.ingestion import chunk_and_store, _sanitize_metadata
from ..rag.retreival import search_chunks
from .pinecone_client import INDEX, NAMESPACE
from ..services.metadata import extract_metadata
from ..model.metadata_model import MetadataRequest

ids: list = []
metadatas: Dict[str, Dict[str, Any]] = {}

def data_ingestion(transcript):
    return chunk_and_store(INDEX, NAMESPACE, metadatas, ids, transcript)

def data_retreival(query, top_k, video_id):
    # perform the search
    matches = search_chunks(query, video_id, top_k)
    # metadata = metadata_fetch(video_id)

    return matches

def data_delete():
    return reset_vector_db(ids, metadatas)

def metadata_fetch(video_id):
    if video_id:
        return metadatas[video_id]
    return {}

def ensure_metadata_loaded(video_id: str, url: str):
    if not video_id or video_id == "unknown":
        return
    if video_id in metadatas and metadatas[video_id]:
        return

    try:
        metadatas[video_id] = metadata_fetch(video_id)
        print(f"Dynamically populated missing metadata for video {video_id}")
    except Exception as e:
        print(f"Failed to dynamically populate metadata for video {video_id}: {str(e)}")