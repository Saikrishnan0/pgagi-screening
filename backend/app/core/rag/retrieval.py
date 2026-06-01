"""
RAG Retrieval Module
---------------------
Given a query + role, retrieves top-K relevant chunks from ChromaDB.
Uses role-scoped filtering so results always come from role-relevant books.
"""

import logging
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from pathlib import Path
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _get_embedder() -> SentenceTransformer:
    logger.info(f"Loading embedder: {settings.embedding_model}")
    return SentenceTransformer(settings.embedding_model)


@lru_cache(maxsize=1)
def _get_collection():
    persist_dir = Path(settings.chroma_persist_dir)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_chunks(
    query: str,
    role: str,
    top_k: Optional[int] = None,
) -> List[Dict]:
    """
    Retrieve top-K relevant chunks for a query, filtered by role.

    Returns a list of dicts:
        {text, source_file, display_name, chunk_index, distance}
    """
    top_k = top_k or settings.top_k_retrieval
    collection = _get_collection()
    embedder = _get_embedder()

    query_embedding = embedder.encode(query).tolist()

    # Map roles to allow cross-role for advanced_ml (it's a superset)
    role_filter_values = [role]
    if role == "advanced_ml":
        role_filter_values = ["advanced_ml", "ai_ml"]

    # ChromaDB where filter: roles field contains any of the role values
    # We store roles as comma-separated string, so we use $contains-like logic
    # Since ChromaDB doesn't support substring match, we query broadly and filter
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k * 3, 30),   # over-fetch then filter
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"] or not results["ids"][0]:
        return []

    # Filter by role
    filtered = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        stored_roles = meta.get("roles", "").split(",")
        if any(r in stored_roles for r in role_filter_values):
            filtered.append({
                "text": doc,
                "source_file": meta.get("source_file", ""),
                "display_name": meta.get("display_name", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "distance": round(dist, 4),
            })
        if len(filtered) >= top_k:
            break

    # If not enough role-filtered results, fall back to all results
    if len(filtered) < 2:
        logger.warning(f"Sparse results for role '{role}', using unfiltered results.")
        filtered = [
            {
                "text": doc,
                "source_file": meta.get("source_file", ""),
                "display_name": meta.get("display_name", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "distance": round(dist, 4),
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ][:top_k]

    return filtered


def retrieve_for_profile(
    profile: Dict,
    role: str,
    num_queries: int = 4,
) -> List[Dict]:
    """
    Build multiple retrieval queries from the candidate's profile,
    deduplicate results, and return a rich context pool.
    """
    skills = profile.get("skills", [])
    tech = profile.get("technologies", [])
    domains = profile.get("domains", [])

    # Craft diverse queries from profile
    queries = []

    # Role-level query
    role_label = role.replace("_", " ")
    queries.append(f"core concepts and fundamentals for {role_label} engineer")

    # Skill-specific queries
    for skill in skills[:3]:
        queries.append(f"{skill} theory and applications in machine learning")

    # Tech-specific
    if tech:
        tech_str = ", ".join(tech[:3])
        queries.append(f"practical applications of {tech_str} in ML systems")

    # Domain-specific
    for domain in domains[:2]:
        queries.append(f"{domain} machine learning techniques and algorithms")

    # Collect and deduplicate chunks
    seen_texts = set()
    all_chunks = []
    for query in queries[:num_queries]:
        chunks = retrieve_chunks(query, role, top_k=3)
        for chunk in chunks:
            if chunk["text"] not in seen_texts:
                seen_texts.add(chunk["text"])
                all_chunks.append(chunk)

    return all_chunks
