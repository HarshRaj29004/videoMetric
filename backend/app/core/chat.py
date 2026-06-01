from ..rag.delete import reset_vector_db
from ..rag.ingestion import chunk_and_store
from ..rag.retreival import search_chunks
from .pinecone_client import INDEX, NAMESPACE

# in-memory session lists kept here
ids: list = []
metadatas: list = []

def data_ingestion(transcript):
    return chunk_and_store(INDEX, NAMESPACE, metadatas, ids, transcript)

def data_retreival(query, top_k, video_id):
    # perform the search
    matches = search_chunks(query, video_id, top_k)
    # find metadata for the requested video in the session store (if any)
    metadata = {}
    if video_id:
        for m in metadatas:
            if str(m.get("video_id")) == str(video_id):
                metadata = m
                break

    return matches, metadata

def data_delete():
    return reset_vector_db(ids, metadatas)