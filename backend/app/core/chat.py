from typing import Any, Dict

from ..rag.delete import reset_vector_db
from ..rag.ingestion import chunk_and_store
from ..rag.retreival import search_chunks
from .pinecone_client import INDEX, NAMESPACE

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