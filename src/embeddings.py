from __future__ import annotations

from typing import List

from .providers import get_embedder


class EmbeddingClient:
    def __init__(self) -> None:
        self._embedder = get_embedder()

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns list of float vectors."""
        return self._embedder.embed(texts)

    def embed_one(self, text: str) -> List[float]:
        return self._embedder.embed_one(text)
