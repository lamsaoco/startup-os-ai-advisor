import os
import json
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.api.common.trigger_dag import trigger_dag as airflow_trigger_dag

import sys
sys.path.append('/opt/airflow')

from ingestion.loader import get_connection, get_db_last_edited_times
from ingestion.notion_crawler import NotionCrawler
from ingestion.config import NOTION_ROOT_PAGE_ID

ALERT_EMAIL = os.getenv("ALERT_EMAIL", "admin@example.com")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [ALERT_EMAIL],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
}

def extract_notion(**context):
    """Crawl Notion pages and save only changed pages to the bronze layer.

    Compares each page's last_edited timestamp against the DB state.
    If no pages have changed, skips writing the bronze file entirely
    and signals the trigger task to abort gracefully.
    """
    # Get DB connection and current state (page_id -> last_edited)
    try:
        conn = get_connection()
        db_state = get_db_last_edited_times(conn)
        conn.close()
    except Exception as e:
        print(f"Warning: Could not connect to DB to get state (first run?): {e}")
        db_state = {}

    crawler = NotionCrawler()
    pages = crawler.crawl(NOTION_ROOT_PAGE_ID, db_state=db_state)

    # Filter to only pages that have actually changed
    changed_pages = [p for p in pages if getattr(p, "is_changed", True)]
    total = len(pages)
    changed = len(changed_pages)

    print(f"[Extract] Crawled {total} pages total — {changed} changed, {total - changed} unchanged (skipped).")

    if not changed_pages:
        # Nothing to process — signal trigger task to skip and exit cleanly
        print("[Extract] No changes detected. Skipping bronze write and DAG 02 trigger.")
        context['ti'].xcom_push(key='bronze_file', value=None)
        return

    # Serialize only the changed pages to the bronze file
    os.makedirs("/opt/airflow/data/bronze", exist_ok=True)
    filename = f"/opt/airflow/data/bronze/crawled_pages_{context['ds']}.json"

    pages_dict = [
        {
            "page_id": p.page_id,
            "title": p.title,
            "parent_id": p.parent_id,
            "breadcrumb": p.breadcrumb,
            "breadcrumb_list": p.breadcrumb_list,
            "url": p.url,
            "last_edited": p.last_edited,
            "blocks": p.blocks,
            "is_changed": True,  # All entries here are confirmed changed
        }
        for p in changed_pages
    ]

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(pages_dict, f, ensure_ascii=False)

    print(f"[Extract] Wrote {changed} changed pages to: {filename}")
    # Push filename to XCom for the trigger task to pick up
    context['ti'].xcom_push(key='bronze_file', value=filename)


def trigger_transform_load(**context):
    """Read the bronze_file path from XCom and trigger DAG 02 with the correct conf.

    TriggerDagRunOperator does NOT evaluate Jinja templates inside `conf`, so
    we use a PythonOperator to read XCom explicitly and call trigger_dag directly.
    If bronze_file is None it means no pages changed — skip triggering DAG 02.
    """
    bronze_file = context['ti'].xcom_pull(
        task_ids='extract_notion',
        key='bronze_file',
    )

    if not bronze_file:
        # extract_notion signalled that there is nothing to process
        print("[Trigger] No bronze file produced — nothing changed. Skipping DAG 02.")
        return

    print(f"[Trigger] Handing off bronze_file to DAG 02: {bronze_file}")
    airflow_trigger_dag(
        dag_id='02_notion_transform_load',
        conf={'bronze_file': bronze_file},
        replace_microseconds=False,
    )


with DAG(
    '01_notion_extraction',
    default_args=default_args,
    description='Extract Notion data to Bronze layer',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    extract_task = PythonOperator(
        task_id='extract_notion',
        python_callable=extract_notion,
        provide_context=True,
    )

    trigger_task = PythonOperator(
        task_id='trigger_transform_load',
        python_callable=trigger_transform_load,
        provide_context=True,
    )

    extract_task >> trigger_task
