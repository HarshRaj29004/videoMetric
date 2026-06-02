import inspect
from typing import Any, Dict, List
import logging
from ..core.pinecone_client import INDEX, NAMESPACE

logging.basicConfig(level=logging.INFO)


def _query_index_with_text(query: str, top_k: int, video_id: str) -> Any:
    search_payload = {
        "namespace": NAMESPACE,
        "top_k": top_k,
        "inputs": {"text": query},
    }
    if video_id:
        search_payload["filter"] = {"video_id": video_id}
    if hasattr(INDEX, "search_records"):
        try:
            return INDEX.search_records(**search_payload)
        except Exception as e:
            print("search_records failed:", repr(e))

    if hasattr(INDEX, "query_records"):
        try:
            return INDEX.query_records(**search_payload)
        except Exception as e:
            print("query_records failed:", repr(e))

    if hasattr(INDEX, "search"):
        try:
            return INDEX.search(**search_payload)
        except Exception as e:
            print("search failed:", repr(e))

    if hasattr(INDEX, "query"):
        try:
            return INDEX.query(**search_payload)
        except Exception as e:
            print("query failed:", repr(e))
    # print(inspect.signature(INDEX.search_records))
    # print(inspect.signature(INDEX.search))
    # print(inspect.signature(INDEX.query))

    raise RuntimeError(
        "Index does not expose a text-search method; expected one of search_records, query_records, search, or query"
    )


def search_chunks(query: str, video_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if INDEX is None:
        logging.warning("Pinecone index not configured; search skipped.")
        return []
    # print(type(INDEX))
    # print(dir(INDEX))
    try:
        response = _query_index_with_text(query, top_k, video_id)
    except Exception as e:
        logging.exception("Pinecone query failed: %s", e)
        return []
    # print(type(response.result))
    # print(dir(response.result))
    matches: List[Dict[str, Any]] = []
    matches_list: List[Dict[str, Any]] = []

    if isinstance(response, list):
        for item in response:
            if isinstance(item, dict):
                matches_list.extend(item.get("matches", []))
    elif isinstance(response, dict):
        matches_list = response.get("matches", []) or response.get("results", [])
    else:
        matches_list = response.result.hits
    # print(matches_list)
    for match_obj in matches_list:
        match = match_obj.fields or {}
        metadata = match.get("metadata") or {}
        content = metadata.get("text") or metadata.get("content") or match.get("payload") or match.get("text") or ""
        matches.append(
            {
                "id": match.get("_id"),
                "content": content,
                "metadata": match.get("metadata"),
            }
        )

    return matches
