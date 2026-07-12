"""embedding.py - offline PDF -> Chroma embedding step (Phase 2).

Standalone, offline module that:
1. Extracts text from the Python Developer job description PDF (PyPDF2).
2. Splits it into overlapping chunks.
3. Embeds each chunk with the OpenAI embeddings model.
4. Persists the chunks + embeddings into a Chroma collection on disk.

This follows the course RAG pattern (lecture 22): raw chromadb plus
client.embeddings.create(...), collection.add(documents=, embeddings=, ids=),
and collection.query(query_embeddings=, n_results=). The only addition is a
Chroma PersistentClient so the collection survives between runs, which the
project spec requires.

Build the collection:
    python -m app.modules.embedding

The Info Advisor (Phase 4) reuses get_collection() and retrieve() from here.
"""

import re

from app.modules import config


def _get_openai_client():
    """Return an OpenAI client, loading OPENAI_API_KEY from .env first."""
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()  # reads OPENAI_API_KEY from the project .env
    return OpenAI()


def extract_pdf_text(path=config.JOB_DESCRIPTION_PDF) -> str:
    """Extract all text from the job-description PDF using PyPDF2."""
    from PyPDF2 import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() for page in reader.pages
                     if page.extract_text())


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping character windows.

    Whitespace is normalized first so chunks are stable regardless of how the
    PDF laid out lines. Overlap keeps context from being cut across a boundary.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(text), step):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def embed_texts(texts: list[str], client=None, model: str = config.EMBEDDING_MODEL):
    """Embed a list of texts with the OpenAI embeddings model (course pattern)."""
    client = client or _get_openai_client()
    response = client.embeddings.create(input=texts, model=model)
    return [list(item.embedding) for item in response.data]


def _get_chroma_client():
    """Return a Chroma PersistentClient rooted at the configured directory."""
    import chromadb

    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def get_collection():
    """Return the persisted job-description collection (must be built first)."""
    return _get_chroma_client().get_or_create_collection(
        name=config.CHROMA_COLLECTION)


def build_collection(pdf_path=config.JOB_DESCRIPTION_PDF,
                     chunk_size: int = 500, overlap: int = 100) -> dict:
    """Build (or rebuild) the Chroma collection from the job-description PDF.

    Returns a small summary dict so callers can report what was persisted.
    """
    text = extract_pdf_text(pdf_path)
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        raise ValueError(f"No text extracted from {pdf_path}")

    client = _get_openai_client()
    embeddings = embed_texts(chunks, client=client)

    chroma = _get_chroma_client()
    # Rebuild from scratch so repeated runs do not accumulate duplicate ids.
    try:
        chroma.delete_collection(name=config.CHROMA_COLLECTION)
    except Exception:
        pass  # collection did not exist yet
    collection = chroma.create_collection(name=config.CHROMA_COLLECTION)

    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": pdf_path.name, "chunk_index": i}
                 for i in range(len(chunks))]
    collection.add(documents=chunks, embeddings=embeddings,
                   ids=ids, metadatas=metadatas)

    return {
        "pdf": str(pdf_path),
        "total_chars": len(text),
        "num_chunks": len(chunks),
        "embedding_model": config.EMBEDDING_MODEL,
        "collection": config.CHROMA_COLLECTION,
        "persist_dir": str(config.CHROMA_DIR),
        "count_in_collection": collection.count(),
    }


def retrieve(query: str, n_results: int = 3, client=None) -> dict:
    """Embed a query with the same model and return the nearest chunks."""
    query_embedding = embed_texts([query], client=client)[0]
    collection = get_collection()
    return collection.query(query_embeddings=[query_embedding],
                            n_results=n_results)


def _main() -> None:
    """Build the collection and run one sample retrieval as a smoke test."""
    print("Building Chroma collection from the job description ...")
    summary = build_collection()
    for key, value in summary.items():
        print(f"  {key:20}: {value}")

    print("\nRetrieval smoke test:")
    sample_query = "What are the required skills for this role?"
    print(f"  query: {sample_query!r}")
    results = retrieve(sample_query, n_results=3)
    for rank, (doc, dist) in enumerate(
            zip(results["documents"][0], results["distances"][0]), start=1):
        print(f"\n  [{rank}] distance={dist:.4f}")
        print(f"      {doc[:200]}")


if __name__ == "__main__":
    _main()
