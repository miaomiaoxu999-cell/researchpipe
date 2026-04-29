"""PDF text extraction + token-aware chunking with page boundary tracking.

Returns chunks of ~target tokens with overlap, each tagged with the dominant page.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF
import tiktoken

ENC = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    chunk_idx: int
    page_no: int  # dominant page (the one with most chars in this chunk)
    content: str
    token_count: int


def extract_pages(pdf_path: str) -> tuple[list[str], dict]:
    """Open PDF and return per-page text + metadata.

    Returns (pages_text, info) where info has:
        n_pages, total_chars, looks_scanned (heuristic).
    Raises on unreadable PDF.
    """
    doc = fitz.open(pdf_path)
    pages: list[str] = []
    total_chars = 0
    try:
        for page in doc:
            text = page.get_text("text") or ""
            text = _normalize(text)
            pages.append(text)
            total_chars += len(text)
    finally:
        doc.close()
    n_pages = len(pages)
    avg_chars_per_page = total_chars / max(n_pages, 1)
    looks_scanned = n_pages > 0 and avg_chars_per_page < 50
    return pages, {
        "n_pages": n_pages,
        "total_chars": total_chars,
        "avg_chars_per_page": round(avg_chars_per_page, 1),
        "looks_scanned": looks_scanned,
    }


_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n{3,}")


def _normalize(t: str) -> str:
    # Strip NULL bytes (PG TEXT rejects 0x00) and other control chars except \n \t
    t = t.replace("\x00", "")
    t = "".join(c for c in t if c == "\n" or c == "\t" or ord(c) >= 32)
    t = _WHITESPACE_RE.sub(" ", t)
    t = _NEWLINES_RE.sub("\n\n", t)
    return t.strip()


def chunk_pages(
    pages: list[str],
    *,
    target_tokens: int = 450,
    overlap_tokens: int = 50,
    min_chunk_tokens: int = 80,
) -> list[Chunk]:
    """Split pages into chunks of ~target_tokens with overlap_tokens.

    Strategy:
      - Concat pages with `\n\n=== Page N ===\n\n` markers (used to track page_no per chunk).
      - Tokenize entire doc once with cl100k_base.
      - Slide a window of target_tokens with overlap_tokens stride.
      - For each chunk, decode tokens → text → derive dominant page from page markers.
    """
    if not pages:
        return []

    # Build doc with page markers
    parts = []
    for i, p in enumerate(pages, start=1):
        if not p.strip():
            continue
        parts.append(f"\n\n=== Page {i} ===\n\n{p}")
    full = "".join(parts).strip()
    if not full:
        return []

    tokens = ENC.encode(full)
    if len(tokens) < min_chunk_tokens:
        # Whole doc in one tiny chunk
        page_no = _dominant_page(full) or 1
        return [Chunk(chunk_idx=0, page_no=page_no, content=full, token_count=len(tokens))]

    chunks: list[Chunk] = []
    stride = max(target_tokens - overlap_tokens, 1)
    idx = 0
    pos = 0
    while pos < len(tokens):
        end = min(pos + target_tokens, len(tokens))
        chunk_tokens = tokens[pos:end]
        text = ENC.decode(chunk_tokens).strip()
        if len(chunk_tokens) >= min_chunk_tokens or not chunks:
            page_no = _dominant_page(text) or _last_page_before(text, chunks) or 1
            chunks.append(
                Chunk(chunk_idx=idx, page_no=page_no, content=text, token_count=len(chunk_tokens))
            )
            idx += 1
        if end >= len(tokens):
            break
        pos += stride
    return chunks


_PAGE_MARKER_RE = re.compile(r"=== Page (\d+) ===")


def _dominant_page(text: str) -> int | None:
    """Find which page-marker number appears most in this chunk."""
    matches = _PAGE_MARKER_RE.findall(text)
    if not matches:
        return None
    counts: dict[int, int] = {}
    for m in matches:
        n = int(m)
        counts[n] = counts.get(n, 0) + 1
    return max(counts, key=counts.get)


def _last_page_before(text: str, prior: list[Chunk]) -> int | None:
    """When chunk has no page marker, inherit from previous chunk."""
    return prior[-1].page_no if prior else None


# ─────────────────────────────────────────────────────────────────────────
# Convenience
# ─────────────────────────────────────────────────────────────────────────


def chunk_pdf(pdf_path: str, **kwargs) -> tuple[list[Chunk], dict]:
    """Extract + chunk a PDF in one call. Returns (chunks, info)."""
    pages, info = extract_pages(pdf_path)
    if info["looks_scanned"]:
        return [], info
    chunks = chunk_pages(pages, **kwargs)
    info["n_chunks"] = len(chunks)
    return chunks, info


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m corpus.chunker <pdf_path>")
        sys.exit(1)
    chunks, info = chunk_pdf(sys.argv[1])
    print(f"info: {info}")
    print(f"chunks: {len(chunks)}")
    for c in chunks[:3]:
        print(f"  chunk_idx={c.chunk_idx} page={c.page_no} tokens={c.token_count}")
        print(f"  preview: {c.content[:200]!r}")
        print()
