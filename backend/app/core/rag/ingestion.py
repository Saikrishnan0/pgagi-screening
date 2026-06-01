"""
Knowledge Base Ingestion Pipeline
----------------------------------
Loads PDFs from knowledge_base/, chunks them, generates embeddings
via sentence-transformers, and persists them into ChromaDB.

Run once (or re-run to refresh):
    python -m app.core.rag.ingestion
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Role → book file mapping ──────────────────────────────────────────────────
ROLE_BOOK_MAP: Dict[str, List[str]] = {
    "ai_ml": [
        "mitchell_ml.pdf",
        "hundred_page_ml.pdf",
        "ml_absolute_beginners.pdf",
        "ai_ml_deep_learning.pdf",
    ],
    "data_science": [
        "intro_ml_python.pdf",
        "master_ml_algorithms.pdf",
    ],
    "advanced_ml": [
        "bishop_pattern_recognition.pdf",
        "ai_ml_deep_learning.pdf",
    ],
}

# Friendly display names for traceability
BOOK_DISPLAY_NAMES: Dict[str, str] = {
    "mitchell_ml.pdf": "Machine Learning — Tom Mitchell",
    "hundred_page_ml.pdf": "The Hundred-Page Machine Learning Book — Burkov",
    "ml_absolute_beginners.pdf": "Machine Learning for Absolute Beginners",
    "ai_ml_deep_learning.pdf": "AI, Machine Learning & Deep Learning",
    "intro_ml_python.pdf": "Introduction to ML with Python",
    "master_ml_algorithms.pdf": "Master ML Algorithms — Jason Brownlee",
    "bishop_pattern_recognition.pdf": "Pattern Recognition and ML — Bishop",
}


def _get_chroma_client() -> chromadb.PersistentClient:
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _get_or_create_collection(client: chromadb.PersistentClient):
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract clean text from a PDF using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        text = page.get_text("text")
        # Normalise whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


def _chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> List[str]:
    """
    Sliding-window chunking at sentence boundaries.
    Preserves context while keeping chunks under token budget.
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    # Split at sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for sentence in sentences:
        slen = len(sentence)
        if current_len + slen > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Overlap: keep last N chars worth of sentences
            overlap_chunk: List[str] = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) <= overlap:
                    overlap_chunk.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current_chunk = overlap_chunk
            current_len = overlap_len

        current_chunk.append(sentence)
        current_len += slen

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return [c.strip() for c in chunks if len(c.strip()) > 80]


def ingest_knowledge_base(kb_dir: str = None, force_reingest: bool = False) -> Dict:
    """
    Main ingestion entry point.
    Returns stats: {role: {book: chunk_count}}.
    """
    kb_path = Path(kb_dir or "knowledge_base")
    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base directory not found: {kb_path}")

    client = _get_chroma_client()
    collection = _get_or_create_collection(client)

    # Load embedding model
    logger.info(f"Loading embedding model: {settings.embedding_model}")
    embedder = SentenceTransformer(settings.embedding_model)

    stats: Dict = {}
    all_pdf_files = list(kb_path.glob("*.pdf"))
    logger.info(f"Found {len(all_pdf_files)} PDFs in {kb_path}")

    for pdf_file in all_pdf_files:
        filename = pdf_file.name
        display_name = BOOK_DISPLAY_NAMES.get(filename, filename)

        # Determine which roles this book belongs to
        book_roles = [
            role for role, books in ROLE_BOOK_MAP.items() if filename in books
        ]
        if not book_roles:
            logger.warning(f"No role mapping for {filename}, skipping.")
            continue

        # Skip if already ingested (unless forced)
        if not force_reingest:
            existing = collection.get(where={"source_file": filename}, limit=1)
            if existing["ids"]:
                logger.info(f"Skipping {filename} (already ingested)")
                continue

        logger.info(f"Ingesting: {display_name}")
        raw_text = _extract_text_from_pdf(pdf_file)
        chunks = _chunk_text(raw_text)
        logger.info(f"  → {len(chunks)} chunks")

        # Batch embed
        embeddings = embedder.encode(chunks, show_progress_bar=True, batch_size=32)

        # Prepare ChromaDB batch
        ids, docs, embeds, metas = [], [], [], []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{filename.replace('.pdf', '')}_{i:05d}"
            ids.append(chunk_id)
            docs.append(chunk)
            embeds.append(embedding.tolist())
            metas.append({
                "source_file": filename,
                "display_name": display_name,
                "roles": ",".join(book_roles),
                "chunk_index": i,
                "chunk_total": len(chunks),
            })

        # Upsert in batches of 500
        batch = 100
        for start in range(0, len(ids), batch):
            collection.upsert(
                ids=ids[start:start + batch],
                documents=docs[start:start + batch],
                embeddings=embeds[start:start + batch],
                metadatas=metas[start:start + batch],
            )

        for role in book_roles:
            stats.setdefault(role, {})[display_name] = len(chunks)

    logger.info("Ingestion complete.")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = ingest_knowledge_base()
    for role, books in result.items():
        print(f"\n[{role}]")
        for book, count in books.items():
            print(f"  {book}: {count} chunks")
