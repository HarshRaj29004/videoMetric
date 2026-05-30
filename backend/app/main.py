from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_frontend_origin
# from .rag import InMemoryRAGStore, build_context, generate_answer, seed_store
from .schemas import AskRequest, AskResponse, DocumentCreate, DocumentRead, RetrievedDocument
from .api.scrape_route import router as scrape_router

app = FastAPI(title="videoMetric RAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_frontend_origin()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# store = InMemoryRAGStore()
# seed_store(store)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "videoMetric RAG API is running"}

app.include_router(scrape_router)

# @app.get("/documents", response_model=list[DocumentRead])
# def list_documents() -> list[DocumentRead]:
#     return [
#         DocumentRead(id=document.id, title=document.title, content=document.content, metadata=document.metadata)
#         for document in store.list_documents()
#     ]


# @app.post("/documents", response_model=DocumentRead)
# def create_document(payload: DocumentCreate) -> DocumentRead:
#     document = store.add_document(payload.title, payload.content, payload.metadata)
#     return DocumentRead(
#         id=document.id,
#         title=document.title,
#         content=document.content,
#         metadata=document.metadata,
#     )


# @app.post("/ask", response_model=AskResponse)
# def ask_question(payload: AskRequest) -> AskResponse:
#     matches = store.search(payload.question, payload.top_k)
#     context = build_context(matches)
#     answer = generate_answer(payload.question, matches)
#     return AskResponse(
#         question=payload.question,
#         answer=answer,
#         context=context,
#         sources=[
#             RetrievedDocument(
#                 id=document.id,
#                 title=document.title,
#                 content=document.content,
#                 score=score,
#                 metadata=document.metadata,
#             )
#             for document, score in matches
#         ],
#     )
