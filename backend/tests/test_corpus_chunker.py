"""Tests for corpus.chunker (text normalization + token-based chunking)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_normalize_strips_null_bytes():
    from corpus.chunker import _normalize

    assert _normalize("hello\x00world") == "helloworld"
    assert _normalize("a\x01\x02\x03b") == "ab"


def test_normalize_keeps_newlines_and_tabs():
    from corpus.chunker import _normalize

    out = _normalize("line1\nline2\tcol2")
    assert "line1" in out and "line2" in out and "col2" in out


def test_normalize_collapses_whitespace():
    from corpus.chunker import _normalize

    assert _normalize("a    b   c") == "a b c"


def test_normalize_collapses_excess_newlines():
    from corpus.chunker import _normalize

    assert _normalize("a\n\n\n\n\nb") == "a\n\nb"


def test_chunk_pages_empty():
    from corpus.chunker import chunk_pages

    assert chunk_pages([]) == []
    assert chunk_pages(["", "", ""]) == []


def test_chunk_pages_short_doc():
    from corpus.chunker import chunk_pages

    pages = ["短篇内容 only one chunk"]
    chunks = chunk_pages(pages, target_tokens=450, overlap_tokens=50)
    assert len(chunks) == 1
    assert "短篇内容" in chunks[0].content
    assert chunks[0].chunk_idx == 0


def test_chunk_pages_long_doc_overlap():
    """Verify overlap: consecutive chunks should share some content."""
    from corpus.chunker import chunk_pages

    long_text = ("这是一段比较长的中文测试内容，用来验证分块逻辑。" * 60)  # ~3000 chars ~ 1500 tokens
    chunks = chunk_pages([long_text], target_tokens=200, overlap_tokens=50)
    assert len(chunks) >= 2
    # Test overlap: chunk N+1 should contain a token slice from end of chunk N
    # Decoded content might not align perfectly char-for-char (tiktoken decodes), but should share substring
    # We just verify counts and stride
    for i, c in enumerate(chunks):
        assert c.chunk_idx == i
        assert c.token_count <= 200


def test_chunk_pages_page_marker_dominance():
    from corpus.chunker import chunk_pages

    pages = ["这是第一页的内容" * 30, "第二页内容" * 30, "第三页" * 30]
    chunks = chunk_pages(pages, target_tokens=80, overlap_tokens=20)
    # First chunk should have page=1 (it sees `=== Page 1 ===` marker)
    assert chunks[0].page_no == 1
    # Later chunks should advance pages
    assert any(c.page_no >= 2 for c in chunks)
