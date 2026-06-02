from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from .chat_model import VideoContext

class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRead(BaseModel):
    id: str
    title: str
    content: str
    metadata: dict[str, Any]


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    video_id: str | None = None


class RetrievedDocument(BaseModel):
    id: str
    title: str
    content: str
    score: int
    metadata: dict[str, Any]


class AskResponse(BaseModel):
    question: str
    answer: str
    context: str
    sources: list[RetrievedDocument]


class ChatRequest(BaseModel):
    query: str
    userContent: list[VideoContext]
    user_id: str
    chat_id: str


class ChatResponse(BaseModel):
    query: str
    video_ids: list[str]
    user_id: str
    chat_id: str
    answer: str
