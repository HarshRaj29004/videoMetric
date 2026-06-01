from typing import Any, Dict, List
import logging
from ..core.pinecone_client import INDEX, NAMESPACE

logging.basicConfig(level=logging.INFO)


def _query_index_with_text(query: str, top_k: int, video_id: str) -> Any:
    search_payload = {
        "inputs": {"text": query},
        "top_k": top_k,
    }
    # include a video_id filter only when provided
    if video_id:
        search_payload["filter"] = {"video_id": video_id}

    if hasattr(INDEX, "search_records"):
        try:
            return INDEX.search_records(namespace=NAMESPACE, query=search_payload)
        except TypeError:
            pass

    if hasattr(INDEX, "query_records"):
        try:
            return INDEX.query_records(namespace=NAMESPACE, query=search_payload)
        except TypeError:
            pass

    if hasattr(INDEX, "search"):
        try:
            return INDEX.search(namespace=NAMESPACE, query=search_payload)
        except TypeError:
            pass

    if hasattr(INDEX, "query"):
        try:
            return INDEX.query(namespace=NAMESPACE, **search_payload)
        except TypeError:
            pass

    raise RuntimeError(
        "Index does not expose a text-search method; expected one of search_records, query_records, search, or query"
    )


def search_chunks(query: str, video_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if INDEX is None:
        logging.warning("Pinecone index not configured; search skipped.")
        return []

    try:
        response = _query_index_with_text(query, top_k, video_id)
    except Exception as e:
        logging.exception("Pinecone query failed: %s", e)
        return []

    matches: List[Dict[str, Any]] = []
    matches_list: List[Dict[str, Any]] = []

    if isinstance(response, list):
        for item in response:
            if isinstance(item, dict):
                matches_list.extend(item.get("matches", []))
    elif isinstance(response, dict):
        matches_list = response.get("matches", []) or response.get("results", [])
    else:
        matches_list = getattr(response, "matches", []) or getattr(response, "results", [])

    for match in matches_list:
        metadata = match.get("metadata") or {}
        content = metadata.get("text") or metadata.get("content") or match.get("payload") or match.get("text") or ""
        matches.append(
            {
                "id": match.get("id"),
                "content": content,
                "metadata": match.get("metadata"),
            }
        )

    return matches
