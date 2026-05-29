from __future__ import annotations

import os


def get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def get_frontend_origin() -> str:
    return os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip() or "http://localhost:5173"
