from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .model.schemas import AskRequest, AskResponse, DocumentCreate, DocumentRead, RetrievedDocument
from .api.route import router as ingestion_router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="videoMetric RAG API", version="0.1.0")
FRONTEND = os.getenv("FRONTEND_ORIGIN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND],
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

app.include_router(ingestion_router)
