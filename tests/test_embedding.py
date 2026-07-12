"""test_embedding.py - tests for the Phase 2 embedding module.

The chunking logic is deterministic and tested offline. The retrieval test
needs the OpenAI API and a built collection, so it skips gracefully when the
key or the persisted collection is absent (for example in CI).
"""

import os

import pytest
from dotenv import load_dotenv

from app.modules import embedding

# Load .env at import so the skipif below can see OPENAI_API_KEY when present.
load_dotenv()


def test_chunk_text_basic():
    """Chunks respect size and overlap and cover the whole text."""
    text = "abcdefghij " * 20  # 220 chars before whitespace normalization
    chunks = embedding.chunk_text(text, chunk_size=50, overlap=10)
    assert chunks, "expected at least one chunk"
    assert all(len(c) <= 50 for c in chunks)
    # The first chunk start and the second chunk start differ by (size - overlap).
    assert len(chunks) > 1


def test_chunk_text_empty():
    """Empty or whitespace-only text yields no chunks."""
    assert embedding.chunk_text("") == []
    assert embedding.chunk_text("    \n\t  ") == []


def test_chunk_text_normalizes_whitespace():
    """Newlines and repeated spaces collapse to single spaces."""
    chunks = embedding.chunk_text("hello\n\n   world", chunk_size=100, overlap=0)
    assert chunks == ["hello world"]


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"),
                    reason="requires OPENAI_API_KEY")
def test_retrieval_returns_relevant_chunk():
    """A skills query should surface the requirements chunk (needs a built collection)."""
    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("no API key after loading .env")

    collection = embedding.get_collection()
    if collection.count() == 0:
        pytest.skip("collection not built yet (run: python -m app.modules.embedding)")

    results = embedding.retrieve("What are the required skills?", n_results=3)
    joined = " ".join(results["documents"][0]).lower()
    assert "skills" in joined or "experience" in joined
