import os
import json
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys
sys.path.append('/opt/airflow')

# Pipeline imports are intentionally lazy (inside the function body).
# Airflow parses DAG files at startup to register them — top-level imports
# would trigger fastembed to download the ONNX model immediately, causing
# a HuggingFace cache permission error before any task even runs.

ALERT_EMAIL = os.getenv("ALERT_EMAIL", "admin@example.com")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [ALERT_EMAIL],
    'email_on_failure': True,
    'retries': 0,
}

def _process_bronze_file(bronze_file: str, conn) -> tuple[int, int]:
    """Process a single bronze JSON file: transform, embed, and load all pages into the DB.

    Returns (pages_processed, total_chunks_loaded).
    Raises on error — file is NOT deleted so it can be retried on the next run.
    """
    from ingestion.notion_crawler import PageData
    from ingestion.chunker import chunk_page
    from ingestion.embedder import embed_chunks
    from ingestion.loader import upsert_document, delete_chunks_for_document, insert_chunks

    with open(bronze_file, "r", encoding="utf-8") as f:
        pages_dict = json.load(f)

    pages = [PageData(**p) for p in pages_dict]
    print(f"[Process] Loaded {len(pages)} pages from: {os.path.basename(bronze_file)}")

    pages_processed = 0
    pages_skipped = 0
    total_chunks = 0

    for i, page in enumerate(pages):
        print(f"  ({i+1}/{len(pages)}) {page.title}")

        # 1. Upsert document metadata
        upsert_document(conn, page)

        if not getattr(page, "is_changed", True):
            print(f"    → Skipped (unchanged)")
            pages_skipped += 1
            continue

        if not page.blocks:
            print(f"    → Skipped (no blocks payload)")
            continue

        # 2. Delete old chunks, then re-chunk and re-embed
        delete_chunks_for_document(conn, page.page_id)

        # chunk_page() expects a full PageData object and extracts text internally
        chunks = chunk_page(page)
        if not chunks:
            continue

        # 3. Embed and store
        embeddings = embed_chunks(chunks)
        insert_chunks(conn, chunks, embeddings)
        conn.commit()

        total_chunks += len(chunks)
        pages_processed += 1
        print(f"    → Loaded {len(chunks)} chunks")

    print(f"  Done: {pages_processed} processed, {pages_skipped} skipped, {total_chunks} chunks total.")
    return pages_processed, total_chunks


def transform_and_load(**context):
    # Lazy imports — deferred until task execution time (not DAG parse time)
    from ingestion.loader import get_connection, init_schema

    conn = get_connection()
    init_schema(conn)

    bronze_dir = "/opt/airflow/data/bronze"

    # Collect the file passed by DAG 01 + any leftover files from previous failed runs.
    # Processing leftovers avoids re-crawling Notion just because DAG 02 failed earlier.
    triggered_file = context['dag_run'].conf.get('bronze_file')
    all_bronze_files = sorted(
        os.path.join(bronze_dir, f)
        for f in os.listdir(bronze_dir)
        if f.endswith(".json")
    )

    if not all_bronze_files:
        # Nothing in the directory — use only the triggered file (may not exist yet)
        if triggered_file and os.path.exists(triggered_file):
            all_bronze_files = [triggered_file]
        else:
            print("[Transform] No bronze files found. Nothing to process.")
            conn.close()
            return

    print(f"[Transform] Found {len(all_bronze_files)} bronze file(s) to process.")

    failed_files = []
    try:
        for bronze_file in all_bronze_files:
            print(f"\n[Transform] Processing file: {bronze_file}")
            try:
                _process_bronze_file(bronze_file, conn)
                # Only delete the file after successful processing
                os.remove(bronze_file)
                print(f"[Cleanup] Deleted: {bronze_file}")
            except Exception as e:
                # Keep the file on disk so next run can retry it
                print(f"[ERROR] Failed to process {bronze_file}: {e}")
                failed_files.append(bronze_file)
    finally:
        conn.close()

    if failed_files:
        raise RuntimeError(
            f"{len(failed_files)} bronze file(s) failed and were kept for retry: "
            + ", ".join(os.path.basename(f) for f in failed_files)
        )

    print("\n[Transform] All bronze files processed successfully.")


with DAG(
    '02_notion_transform_load',
    default_args=default_args,
    description='Transform Bronze data and Load to Postgres',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    
    transform_load_task = PythonOperator(
        task_id='transform_and_load',
        python_callable=transform_and_load,
        provide_context=True
    )
