"""
Database Logger for Streamlit Application
Records user queries, LLM responses, retrieved chunks, latency, and feedback into PostgreSQL.
"""
import uuid
import datetime
from typing import List, Dict, Any

from ingestion.loader import get_connection

def log_interaction(
    user_query: str,
    rewritten_query: str,
    retrieved_chunks: List[Dict[str, Any]],
    llm_response: str,
    latency_seconds: float
) -> str:
    """
    Log the initial interaction to the database.
    Returns the generated log_id so feedback can be attached later.
    """
    log_id = str(uuid.uuid4())
    latency_ms = int(latency_seconds * 1000)
    chunk_ids = [chunk["chunk_id"] for chunk in retrieved_chunks]
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_monitoring_logs 
                (log_id, user_query, rewritten_query, retrieved_chunks, llm_response, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (log_id, user_query, rewritten_query, chunk_ids, llm_response, latency_ms)
            )
        conn.commit()
    finally:
        conn.close()
        
    return log_id

def log_feedback(log_id: str, rating: int) -> None:
    """
    Update an existing log entry with user feedback.
    rating: +1 (Thumbs Up) or -1 (Thumbs Down)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE app_monitoring_logs SET rating = %s WHERE log_id = %s",
                (rating, log_id)
            )
        conn.commit()
    finally:
        conn.close()
