from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List

import chromadb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .chunker import Chunk, chunk_markdown
from .embeddings import EmbeddingClient

console = Console()

BATCH_SIZE = 50


def _get_chroma_collection(persist_dir: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(
        name="runbooks",
        metadata={"hnsw:space": "cosine"},
    )


def ingest_directory(runbooks_dir: str, persist_dir: str) -> int:
    """
    Ingest all markdown files in runbooks_dir into ChromaDB.
    Returns total number of chunks stored.
    """
    docs_path = Path(runbooks_dir)
    md_files = list(docs_path.glob("**/*.md"))

    if not md_files:
        console.print(f"[yellow]No markdown files found in {runbooks_dir}[/yellow]")
        return 0

    collection = _get_chroma_collection(persist_dir)
    embedder = EmbeddingClient()
    total_chunks = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for md_file in md_files:
            task = progress.add_task(
                f"Ingesting [cyan]{md_file.name}[/cyan]...", total=None
            )
            chunks: List[Chunk] = chunk_markdown(md_file)

            for batch_start in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[batch_start : batch_start + BATCH_SIZE]
                texts = [c.text for c in batch]
                embeddings = embedder.embed(texts)

                collection.upsert(
                    ids=[str(uuid.uuid4()) for _ in batch],
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=[c.metadata for c in batch],
                )

            total_chunks += len(chunks)
            progress.update(
                task,
                description=f"[green]✓[/green] [cyan]{md_file.name}[/cyan] — {len(chunks)} chunks",
            )
            progress.stop_task(task)

    return total_chunks


def clear_collection(persist_dir: str) -> None:
    """Delete and recreate the runbooks collection."""
    client = chromadb.PersistentClient(path=persist_dir)
    try:
        client.delete_collection("runbooks")
        console.print("[yellow]Cleared existing collection.[/yellow]")
    except Exception:
        pass


def collection_stats(persist_dir: str) -> dict:
    """Return basic stats about the stored collection."""
    try:
        collection = _get_chroma_collection(persist_dir)
        count = collection.count()
        return {"total_chunks": count, "collection": "runbooks"}
    except Exception as e:
        return {"error": str(e)}
