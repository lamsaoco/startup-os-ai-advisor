import os
import json
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys
sys.path.append('/opt/airflow')

from ingestion.loader import get_connection, init_schema, upsert_document, delete_chunks_for_document, insert_chunks
from ingestion.notion_crawler import PageData
from ingestion.text_extractor import blocks_to_text
from ingestion.chunker import chunk_page
from ingestion.embedder import embed_chunks

ALERT_EMAIL = os.getenv("ALERT_EMAIL", "admin@example.com")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [ALERT_EMAIL],
    'email_on_failure': True,
    'retries': 0,
}

def transform_and_load(**context):
    # Initialize DB Schema
    conn = get_connection()
    init_schema(conn)
    
    # Get bronze file path from DAG run conf
    bronze_file = context['dag_run'].conf.get('bronze_file')
    if not bronze_file or not os.path.exists(bronze_file):
        raise ValueError(f"Bronze file {bronze_file} not found!")
        
    with open(bronze_file, "r", encoding="utf-8") as f:
        pages_dict = json.load(f)
        
    pages = [PageData(**p) for p in pages_dict]
    print(f"Loaded {len(pages)} pages from bronze layer.")
    
    total_chunks_loaded = 0
    pages_processed = 0
    pages_skipped = 0
    
    for i, page in enumerate(pages):
        print(f"Processing ({i+1}/{len(pages)}): {page.title}")
        
        # 1. Upsert document metadata
        is_changed_in_db = upsert_document(conn, page)
        
        if not getattr(page, "is_changed", True):
            print(f"  → Skipped (unchanged since last sync)")
            pages_skipped += 1
            continue
            
        if not page.blocks:
            print("  → Skipped (changed but no blocks payload found)")
            continue

        # 2. Delete old chunks
        delete_chunks_for_document(conn, page.page_id)

        # 3. Extract text
        markdown_text = blocks_to_text(page.blocks)
        
        # 4. Chunk text
        chunks = chunk_page(page.page_id, markdown_text)
        if not chunks:
            continue
            
        # 5. Embed
        embeddings = embed_chunks(chunks)
        
        # 6. Insert chunks & embeddings
        insert_chunks(conn, chunks, embeddings)
        
        conn.commit()
        
        total_chunks_loaded += len(chunks)
        pages_processed += 1
        print(f"  → Embedded and loaded {len(chunks)} chunks")
        
    conn.close()
    print(f"\nTransform and Load complete! Processed {pages_processed}, Skipped {pages_skipped}, Loaded {total_chunks_loaded} chunks.")


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
