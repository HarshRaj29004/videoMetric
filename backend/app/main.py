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
