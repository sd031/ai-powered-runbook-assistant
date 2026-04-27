from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import chromadb

from .embeddings import EmbeddingClient
from .providers import get_chat

SYSTEM_PROMPT = """\
You are an expert SRE (Site Reliability Engineer) assistant.
You help on-call engineers resolve incidents quickly and accurately.
Answer questions based ONLY on the provided runbook context.
If the answer is not clearly covered in the context, say so and suggest escalation.
Always cite the specific runbook source(s) you used at the end of your answer.
Be concise: prefer numbered step-by-step instructions when applicable.
"""


@dataclass
class QueryResult:
    answer: str
    sources: List[str]
    context_chunks: List[str]
    distances: List[float] = field(default_factory=list)


def _get_chroma_collection(persist_dir: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(
        name="runbooks",
        metadata={"hnsw:space": "cosine"},
    )


def ask(question: str, persist_dir: str, top_k: int = 5) -> QueryResult:
    """
    RAG query: embed question → retrieve top_k chunks → generate answer via configured LLM.
    """
    embedder = EmbeddingClient()
    query_embedding = embedder.embed_one(question)

    collection = _get_chroma_collection(persist_dir)

    if collection.count() == 0:
        return QueryResult(
            answer="The runbook database is empty. Please run `python cli.py ingest` first.",
            sources=[],
            context_chunks=[],
        )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs: List[str] = results["documents"][0]
    metas: List[dict] = results["metadatas"][0]
    distances: List[float] = results["distances"][0]

    context_parts = []
    sources = []
    for doc, meta in zip(docs, metas):
        source = meta.get("source", "unknown")
        header = meta.get("header", "")
        label = f"[{source} — {header}]" if header else f"[{source}]"
        context_parts.append(f"{label}\n{doc}")
        if source not in sources:
            sources.append(source)

    context = "\n\n---\n\n".join(context_parts)

    user_message = f"""Runbook context:
{context}

Incident question: {question}"""

    chat = get_chat()
    answer = chat.complete(SYSTEM_PROMPT, user_message)
    return QueryResult(
        answer=answer,
        sources=sources,
        context_chunks=docs,
        distances=distances,
    )
