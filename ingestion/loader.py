"""
PostgreSQL Loader — inserts documents and chunks (with embeddings) into the database.

Uses upsert (INSERT ... ON CONFLICT DO UPDATE) so the pipeline is safe to re-run:
  - Re-running will update existing records instead of creating duplicates.
  - Chunks are deleted and re-inserted when a document is re-processed
    (detected via last_edited timestamp change).
"""
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

from ingestion.config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    EMBEDDING_DIMENSIONS,
)
from ingestion.chunker import Chunk
from ingestion.notion_crawler import PageData


def get_connection():
    """Create and return a new psycopg2 database connection."""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    # Ensure the vector extension exists before registering the type.
    # Must commit so the extension is visible to the current session.
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    # Register pgvector type so psycopg2 handles vector columns natively
    register_vector(conn)
    return conn


def get_db_last_edited_times(conn) -> dict[str, str]:
    """Return a mapping of page_id to last_edited string for all pages in DB."""
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.documents');")
        if not cur.fetchone()[0]:
            return {}
        cur.execute("SELECT id, last_edited FROM documents")
        rows = cur.fetchall()
        return {row[0]: str(row[1]) for row in rows}


def upsert_document(conn, page: PageData) -> bool:
    """
    Upsert a Notion page record into the documents table.
    Returns True if the page was new or updated (needs re-chunking),
    Returns False if last_edited timestamp is unchanged (skip re-chunking).
    """
    with conn.cursor() as cur:
        # Check if document already exists with the same last_edited timestamp
        cur.execute(
            "SELECT last_edited FROM documents WHERE id = %s",
            (page.page_id,),
        )
        row = cur.fetchone()
        if row and str(row[0]) == page.last_edited:
            return False  # Not changed — skip

        # Upsert document metadata
        cur.execute(
            """
            INSERT INTO documents (id, title, parent_id, breadcrumb, url, last_edited)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title       = EXCLUDED.title,
                parent_id   = EXCLUDED.parent_id,
                breadcrumb  = EXCLUDED.breadcrumb,
                url         = EXCLUDED.url,
                last_edited = EXCLUDED.last_edited
            """,
            (
                page.page_id,
                page.title,
                page.parent_id,
                page.breadcrumb,
                page.url,
                page.last_edited,
            ),
        )
    return True  # New or updated — needs re-chunking


def delete_chunks_for_document(conn, document_id: str) -> None:
    """Delete all existing chunks for a document before re-inserting updated ones."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))


def insert_chunks(conn, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """
    Batch insert chunks with their embedding vectors into the chunks table.
    Uses execute_values for efficient bulk insertion.
    """
    if not chunks:
        return

    rows = [
        (
            chunk.chunk_id,
            chunk.document_id,
            chunk.content,
            chunk.embed_text,
            chunk.heading_path,
            chunk.chunk_index,
            chunk.token_count,
            embedding,  # pgvector handles list[float] → vector conversion
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO chunks
                (chunk_id, document_id, content, embed_text, heading_path,
                 chunk_index, token_count, embedding)
            VALUES %s
            """,
            rows,
        )


def init_schema(conn) -> None:
    """
    Create all required tables and indexes if they do not already exist.
    Safe to call on every startup (uses CREATE IF NOT EXISTS).
    """
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                parent_id   TEXT,
                breadcrumb  TEXT NOT NULL,
                url         TEXT,
                last_edited TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id      TEXT PRIMARY KEY,
                document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                content       TEXT NOT NULL,
                embed_text    TEXT,           -- contextual text used for embedding (breadcrumb + content)
                heading_path  TEXT,
                chunk_index   INTEGER NOT NULL,
                token_count   INTEGER,
                embedding     VECTOR({EMBEDDING_DIMENSIONS}),
                content_tsv   TSVECTOR
                              GENERATED ALWAYS AS (to_tsvector('english', embed_text)) STORED,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # We explicitly DO NOT create an IVFFlat or HNSW index here.
        # With our dataset size (~1200 chunks of 512 tokens), Exact Nearest Neighbor
        # Search (SeqScan) executes in <1ms. Using an approximate index like IVFFlat
        # with default probes=1 caused a severe recall drop (Hit@5 capped at 17%).

        # Full-text search index for BM25 (GIN on tsvector column)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_tsv_idx
                ON chunks USING GIN (content_tsv);
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_monitoring_logs (
                log_id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                user_query      TEXT NOT NULL,
                rewritten_query TEXT,
                retrieved_chunks TEXT[],
                llm_response    TEXT,
                latency_ms      INTEGER,
                rating          SMALLINT DEFAULT 0,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    conn.commit()
    print("[Loader] Schema initialized successfully")
