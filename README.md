# videoMetric RAG Starter

A basic two-part RAG starter with a React frontend and a FastAPI backend.

## Structure

- `frontend/` - React + Vite app
- `backend/` - FastAPI app

## Backend

### Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints

- `GET /health` - health check
- `POST /ask` - ask a question against the basic RAG pipeline
- `POST /documents` - add documents to the in-memory knowledge base
- `GET /documents` - list loaded documents
- `POST /scraper` - extract media metadata from YouTube or Instagram
- `POST /transcript` - extract YouTube captions or transcribe Instagram audio

## Frontend

### Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

The frontend expects the backend at `VITE_API_URL`.

## Notes

This scaffold uses a simple in-memory retrieval layer so you can extend it with a vector database, embeddings, and a production LLM provider later.
