from typing import Any, Callable, Dict, List, Optional
from pinecone import Pinecone
from dotenv import load_dotenv
import os
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)


# def _query_index_with_text(query: str, top_k: int) -> Any:
#     search_payload = {
#         "inputs": {"text": query},
#         "top_k": top_k,
#     }

#     if hasattr(INDEX, "search_records"):
#         try:
#             return INDEX.search_records(namespace="videometric", query=search_payload)
#         except TypeError:
#             pass

#     if hasattr(INDEX, "search"):
#         try:
#             return INDEX.search(namespace="videometric", query=search_payload)
#         except TypeError:
#             pass

#     raise RuntimeError("Pinecone index does not expose a text-search method")


def search_chunks(INDEX,metadatquery: str, top_k: int = 3, embed_fn: Optional[Callable[[str], List[float]]] = None) -> List[Dict[str, Any]]:
    if INDEX is None:
        logging.warning("Pinecone index not configured; search skipped.")
        return []

    try:
        if embed_fn is not None:
            q_vector = embed_fn(query)
            response = INDEX.query(queries=[q_vector], top_k=top_k, include_metadata=True, include_values=False)
        else:
            response = _query_index_with_text(query, top_k)
    except Exception as e:
        logging.exception("Pinecone query failed: %s", e)
        return []

    matches: List[Dict[str, Any]] = []

    # support multiple Pinecone response shapes
    results = response.get("results") or response.get("matches") or []
    matches_list = []
    if isinstance(results, list) and results:
        # newer shape: results -> [{matches: [...]}]
        for r in results[0].get("matches", []):
            matches_list.append(r)
    else:
        matches_list = response.get("matches", [])

    for match in matches_list:
        metadata = match.get("metadata") or {}
        content = metadata.get("text") or metadata.get("content") or match.get("payload") or ""
        matches.append(
            {
                "id": match.get("id"),
                "content": content,
                "metadata": metadata,
                "score": match.get("score") or match.get("distance"),
                "video_id": metadata.get("video_id"),
            }
        )

    return matches
