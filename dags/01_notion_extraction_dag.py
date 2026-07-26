import os
import json
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

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
    # Get DB connection and state
    try:
        conn = get_connection()
        db_state = get_db_last_edited_times(conn)
        conn.close()
    except Exception as e:
        print(f"Warning: Could not connect to DB to get state (first run?): {e}")
        db_state = {}

    crawler = NotionCrawler()
    pages = crawler.crawl(NOTION_ROOT_PAGE_ID, db_state=db_state)
    
    # Save to bronze
    os.makedirs("/opt/airflow/data/bronze", exist_ok=True)
    filename = f"/opt/airflow/data/bronze/crawled_pages_{context['ds']}.json"
    
    # Convert PageData objects to dict
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
            "is_changed": getattr(p, "is_changed", True)
        } for p in pages
    ]
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(pages_dict, f, ensure_ascii=False)
        
    # Pass filename to next DAG
    context['ti'].xcom_push(key='bronze_file', value=filename)

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
        provide_context=True
    )
    
    trigger_transform_load = TriggerDagRunOperator(
        task_id='trigger_transform_load',
        trigger_dag_id='02_notion_transform_load',
        conf={'bronze_file': "{{ ti.xcom_pull(task_ids='extract_notion', key='bronze_file') }}"}
    )
    
    extract_task >> trigger_transform_load
