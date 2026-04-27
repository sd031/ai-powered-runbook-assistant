from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


def _split_by_words(text: str, max_words: int, overlap_words: int) -> List[str]:
    """Split text into word-budget chunks with overlap."""
    words = text.split()
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += max_words - overlap_words
    return chunks


def chunk_markdown(
    file_path: Path,
    max_words: int = 300,
    overlap_words: int = 40,
) -> List[Chunk]:
    """
    Chunk a markdown file into semantically meaningful pieces.
    Splits on H1/H2/H3 headers first, then by word budget.
    """
    text = file_path.read_text(encoding="utf-8")
    filename = file_path.name

    # Split on markdown headers
    header_pattern = re.compile(r"(?=^#{1,3} .+$)", re.MULTILINE)
    sections = header_pattern.split(text)
    sections = [s.strip() for s in sections if s.strip()]

    chunks: List[Chunk] = []
    for section in sections:
        lines = section.splitlines()
        header_line = lines[0] if lines and lines[0].startswith("#") else filename
        header = header_line.lstrip("#").strip()

        sub_chunks = _split_by_words(section, max_words, overlap_words)
        for i, chunk_text in enumerate(sub_chunks):
            if not chunk_text.strip():
                continue
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata={
                        "source": filename,
                        "header": header,
                        "chunk_index": i,
                        "file_path": str(file_path),
                    },
                )
            )
    return chunks
