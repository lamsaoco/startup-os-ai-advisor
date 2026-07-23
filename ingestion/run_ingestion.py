"""
Main ingestion pipeline orchestrator.

Run this script to ingest all Notion pages into PostgreSQL:
    uv run python -m ingestion.run_ingestion             # ingest all pages
    uv run python -m ingestion.run_ingestion --limit 5   # test with first 5 pages

Pipeline steps:
  1. Initialize DB schema
  2. Crawl all pages from Notion (recursive, starting from root page)
  3. For each page: extract text, chunk, generate embeddings, load to DB
  4. Skip pages where last_edited timestamp has not changed (incremental updates)
"""
import argparse
import time

from tqdm import tqdm

from ingestion.config import NOTION_ROOT_PAGE_ID
from ingestion.notion_crawler import NotionCrawler
from ingestion.chunker import chunk_page
from ingestion.embedder import embed_chunks
from ingestion.loader import (
    get_connection,
    init_schema,
    upsert_document,
    delete_chunks_for_document,
    insert_chunks,
)


def run(limit: int = 0):
    """
    Execute the full ingestion pipeline.
    :param limit: If > 0, only process the first N pages (useful for testing).
    """
    print("=" * 60)
    print("  Startup OS AI Advisor — Ingestion Pipeline")
    if limit:
        print(f"  ⚠️  TEST MODE: processing first {limit} pages only")
    print("=" * 60)
    start_time = time.time()

    # ── Step 1: Connect to DB and initialize schema ───────────────────────────
    print("\n[Step 1/4] Connecting to PostgreSQL and initializing schema...")
    conn = get_connection()
    init_schema(conn)

    # ── Step 2: Crawl all pages from Notion ──────────────────────────────────
    print(f"\n[Step 2/4] Crawling Notion pages from root: {NOTION_ROOT_PAGE_ID}")
    crawler = NotionCrawler()
    pages = crawler.crawl(NOTION_ROOT_PAGE_ID)
    print(f"           → {len(pages)} total pages found")

    # Apply limit for test runs
    if limit and limit < len(pages):
        pages = pages[:limit]
        print(f"           → Limiting to first {limit} pages for this test run")

    # ── Step 3: Process each page ────────────────────────────────────────────
    print(f"\n[Step 3/4] Chunking, embedding, and loading {len(pages)} pages...")
    total_chunks_loaded = 0
    skipped_pages = 0

    for page in tqdm(pages, desc="Processing pages"):
        # Upsert document metadata; returns False if page is unchanged
        needs_update = upsert_document(conn, page)
        if not needs_update:
            skipped_pages += 1
            continue

        # Generate text chunks from this page
        chunks = chunk_page(page)
        if not chunks:
            conn.commit()
            continue

        # Generate embeddings for all chunks in this page
        embeddings = embed_chunks(chunks)

        # Delete stale chunks and insert fresh ones
        delete_chunks_for_document(conn, page.page_id)
        insert_chunks(conn, chunks, embeddings)

        conn.commit()
        total_chunks_loaded += len(chunks)

    conn.close()

    # ── Step 4: Summary ───────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print(f"\n[Step 4/4] Done!")
    print(f"           Pages processed : {len(pages) - skipped_pages}")
    print(f"           Pages skipped   : {skipped_pages} (unchanged)")
    print(f"           Chunks loaded   : {total_chunks_loaded}")
    print(f"           Total time      : {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Startup OS AI Advisor — Ingestion Pipeline")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of pages to process (0 = no limit, useful for testing)",
    )
    args = parser.parse_args()
    run(limit=args.limit)
