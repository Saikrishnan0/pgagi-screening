#!/usr/bin/env python3
"""
Run this script ONCE after placing PDFs in the knowledge_base/ directory.
It chunks and embeds all books into ChromaDB for RAG retrieval.

Usage:
    cd backend
    python scripts/ingest.py

To force re-ingestion (e.g. after updating PDFs):
    python scripts/ingest.py --force
"""

import sys
import os
import argparse
import logging

# Ensure app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

from app.core.rag.ingestion import ingest_knowledge_base

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force re-ingestion of all books")
    args = parser.parse_args()

    print("\n🔍 PGAGI Knowledge Base Ingestion")
    print("=" * 45)

    try:
        stats = ingest_knowledge_base(
            kb_dir="../knowledge_base",
            force_reingest=args.force,
        )

        print("\n✅ Ingestion complete!\n")
        total_chunks = 0
        for role, books in stats.items():
            print(f"  [{role}]")
            for book, count in books.items():
                print(f"    • {book}: {count} chunks")
                total_chunks += count

        print(f"\n  Total chunks stored: {total_chunks}")
        print("\nYou can now start the backend server.\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("Make sure you've placed the PDF books in the knowledge_base/ directory.")
        print("Expected filenames:")
        from app.core.rag.ingestion import BOOK_DISPLAY_NAMES
        for fname, display in BOOK_DISPLAY_NAMES.items():
            print(f"  • {fname}  ({display})")
        sys.exit(1)
