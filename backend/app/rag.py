# from __future__ import annotations

# import re
# import uuid
# from dataclasses import dataclass, field
# from typing import Any

# from openai import OpenAI

# from .config import get_openai_api_key, get_openai_model

# WORD_RE = re.compile(r"[A-Za-z0-9']+")


# def _tokenize(text: str) -> set[str]:
#     return {token.lower() for token in WORD_RE.findall(text)}


# @dataclass
# class KnowledgeDocument:
#     id: str
#     title: str
#     content: str
#     metadata: dict[str, Any] = field(default_factory=dict)


# class InMemoryRAGStore:
#     def __init__(self) -> None:
#         self._documents: list[KnowledgeDocument] = []

#     def add_document(self, title: str, content: str, metadata: dict[str, Any] | None = None) -> KnowledgeDocument:
#         document = KnowledgeDocument(
#             id=str(uuid.uuid4()),
#             title=title,
#             content=content,
#             metadata=metadata or {},
#         )
#         self._documents.append(document)
#         return document

#     def list_documents(self) -> list[KnowledgeDocument]:
#         return list(self._documents)

#     def search(self, query: str, top_k: int = 3) -> list[tuple[KnowledgeDocument, int]]:
#         query_tokens = _tokenize(query)
#         ranked: list[tuple[KnowledgeDocument, int]] = []

#         for document in self._documents:
#             document_tokens = _tokenize(f"{document.title} {document.content}")
#             score = len(query_tokens & document_tokens)
#             if score > 0:
#                 ranked.append((document, score))

#         ranked.sort(key=lambda item: item[1], reverse=True)
#         return ranked[:top_k]


# DEFAULT_DOCUMENTS = [
#     {
#         "title": "What is RAG?",
#         "content": "Retrieval-augmented generation combines retrieval with generation so the model can answer from relevant context instead of relying only on memory.",
#         "metadata": {"category": "overview"},
#     },
#     {
#         "title": "Recommended starter flow",
#         "content": "Store documents, create embeddings, retrieve the best matches for a query, then generate a grounded answer with citations.",
#         "metadata": {"category": "architecture"},
#     },
#     {
#         "title": "Next production step",
#         "content": "Replace the in-memory store with a vector database such as pgvector, Pinecone, or Chroma and wire in a durable ingestion pipeline.",
#         "metadata": {"category": "next-step"},
#     },
# ]


# def seed_store(store: InMemoryRAGStore) -> None:
#     if store.list_documents():
#         return

#     for document in DEFAULT_DOCUMENTS:
#         store.add_document(document["title"], document["content"], document["metadata"])


# def build_context(matches: list[tuple[KnowledgeDocument, int]]) -> str:
#     if not matches:
#         return "No matching documents were found."

#     sections: list[str] = []
#     for index, (document, score) in enumerate(matches, start=1):
#         sections.append(
#             f"[{index}] {document.title} (score: {score})\n{document.content}"
#         )
#     return "\n\n".join(sections)


# def generate_answer(question: str, matches: list[tuple[KnowledgeDocument, int]]) -> str:
#     context = build_context(matches)
#     api_key = get_openai_api_key()

#     if api_key:
#         try:
#             client = OpenAI(api_key=api_key)
#             response = client.chat.completions.create(
#                 model=get_openai_model(),
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": "You answer questions using only the provided context. Be concise and mention when the context is insufficient.",
#                     },
#                     {
#                         "role": "user",
#                         "content": f"Question: {question}\n\nContext:\n{context}",
#                     },
#                 ],
#             )
#             return response.choices[0].message.content or "No answer returned by the model."
#         except Exception as exc:
#             return (
#                 "The retrieval step succeeded, but the LLM call failed. "
#                 f"Fallback answer: {exc}"
#             )

#     if not matches:
#         return "No relevant documents were found. Add content to the knowledge base and try again."

#     top_titles = ", ".join(document.title for document, _ in matches)
#     return (
#         "LLM not configured. Based on the retrieved documents, the most relevant sources are: "
#         f"{top_titles}. Use the context above to build a grounded answer."
#     )
