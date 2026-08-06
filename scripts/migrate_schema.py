"""
Schema Migration Script — drops and recreates the chunks table.

Run this ONCE before re-ingesting after changing:
  - EMBEDDING_DIMENSIONS (e.g., 768 → 1024 when switching to bge-large-en-v1.5)
  - Adding new columns (e.g., embed_text)

Usage (runs inside the airflow container which is already in Docker network):
    docker compose exec airflow uv run python -m scripts.migrate_schema

WARNING: This deletes ALL chunks from the database.
         Re-run the Airflow ingestion DAG afterwards.
"""
import sys
from ingestion.config import EMBEDDING_DIMENSIONS
from ingestion.loader import get_connection, init_schema


def migrate() -> None:
    """Drop the chunks table and recreate it with the new schema."""
    print("=" * 60)
    print("Schema Migration")
    print(f"  New embedding dimension : {EMBEDDING_DIMENSIONS}")
    print("=" * 60)
    print()

    # Prompt for confirmation to avoid accidental data loss
    answer = input(
        "WARNING: This will DROP the 'chunks' table and all stored embeddings.\n"
        "You must re-run the full ingestion pipeline afterwards.\n"
        "Type 'yes' to continue: "
    ).strip().lower()

    if answer != "yes":
        print("Aborted.")
        sys.exit(0)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("\n[Migration] Dropping dependent indexes...")
            cur.execute("DROP INDEX IF EXISTS chunks_embedding_idx;")
            cur.execute("DROP INDEX IF EXISTS chunks_tsv_idx;")

            print("[Migration] Dropping chunks table...")
            cur.execute("DROP TABLE IF EXISTS chunks CASCADE;")

        conn.commit()
        print("[Migration] Chunks table dropped successfully.")

        print("[Migration] Recreating schema with new dimensions...")
        init_schema(conn)
        print("[Migration] Schema recreated successfully.")
        print()
        print("Next step: re-run the ingestion pipeline to re-embed all documents.")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
