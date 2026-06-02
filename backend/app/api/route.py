from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..core.data_extraction import get_transcript
from ..model.schemas import AskRequest, AskResponse, RetrievedDocument, ChatRequest, ChatResponse
from ..services.transcript import TranscriptRequest
from ..core.chat import data_delete,data_ingestion,data_retreival,metadata_fetch
from ..core.graph import run_chat_stream

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post('/data-ingest')
def ingestion(payload: TranscriptRequest) -> Dict[str, Any]:
    try:
        transcript = get_transcript(payload)
        storage_result = data_ingestion(transcript)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "ok",
        "source": transcript.get("source"),
        "video_id": storage_result.get("video_id") or transcript.get("video_id"),
        "title": storage_result.get("title",""),
        "chunks_stored": storage_result.get("chunks_stored", 0),
        "metadata_stored": storage_result.get("metadata_stored", False),
    }

@router.post('/data-retreive', response_model=AskResponse)
def retreive(payload: AskRequest) -> AskResponse:
    try:
        matches = data_retreival(payload.question, top_k=payload.top_k,video_id = payload.video_id)
        metadata = metadata_fetch(payload.video_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not matches:
        return AskResponse(
            question=payload.question,
            answer='No matching transcript chunks were found. Add transcript URLs first, or try a different query.',
            context='',
            sources=[],
        )

    sources = []
    context_parts = []
    for index, match in enumerate(matches, start=1):
        content = str(match.get('content', '')).strip()
        context_parts.append(f'[{index}] {content}')
        sources.append(
            RetrievedDocument(
                id=str(match.get('id') or f'chunk-{index}'),
                title=f"{metadata.get('source', 'video')} · {payload.video_id}",
                content=content,
                score=max(1, len(matches) - index + 1),
                metadata={
                    'video_id': metadata.get('video_id'),
                    'source': metadata.get('source'),
                },
            )
        )

    return AskResponse(
        question=payload.question,
        answer=f'Retrieved {len(matches)} relevant transcript chunk(s) from the current session.',
        context='\n\n'.join(context_parts),
        # sources=sources,
    )


@router.delete('/data-delete')
def delete() -> Dict[str, Any]:
    try:
        result = data_delete()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.get("deleted"):
        return {
            "status": "ok",
            "namespace": result.get("namespace", "videometric"),
        }

    detail = result.get("error") or result.get("reason") or "Failed to clear vector database"
    raise HTTPException(status_code=500, detail=detail)

@router.post('/')
async def chat(payload: ChatRequest):
    """
    Handles real-time streaming chat turns by consuming the LangGraph 
    async generator and piping text tokens directly to the client.
    """
    try:
        token_generator = run_chat_stream(
            query=payload.query,
            user_content=payload.userContent,
            user_id=payload.user_id,
            chat_id=payload.chat_id,
        )
        
        return StreamingResponse(
            token_generator, 
            media_type="text/event-stream"
        )
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
