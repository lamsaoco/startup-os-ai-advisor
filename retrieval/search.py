"""
Search Module — implements Hybrid Search (Vector + BM25), Reciprocal Rank Fusion, and Cross-Encoder Reranking.
"""
import os
from typing import List, Dict, Any

from sentence_transformers import CrossEncoder

from ingestion.config import RETRIEVAL_TOP_K, RERANK_TOP_K, CROSS_ENCODER_MODEL

# Initialize Cross-Encoder (SentenceTransformers uses HF_HOME environment variable for cache)
_cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)


def hybrid_search(conn, query_text: str, query_embedding: List[float], top_k: int = RETRIEVAL_TOP_K) -> List[Dict[str, Any]]:
    """
    Executes Hybrid Search combining Vector Search and BM25 using Reciprocal Rank Fusion (RRF).
    """
    sql = """
    WITH vector_search AS (
        SELECT chunk_id,
               RANK() OVER (ORDER BY embedding <=> %s::vector) AS vector_rank
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    ),
    keyword_search AS (
        SELECT chunk_id,
               RANK() OVER (ORDER BY ts_rank_cd(content_tsv, plainto_tsquery('english', %s)) DESC) AS keyword_rank
        FROM chunks
        WHERE content_tsv @@ plainto_tsquery('english', %s)
        ORDER BY ts_rank_cd(content_tsv, plainto_tsquery('english', %s)) DESC
        LIMIT %s
    )
    SELECT
        c.chunk_id,
        c.content,
        c.heading_path,
        d.breadcrumb,
        COALESCE(1.0 / (60 + v.vector_rank), 0.0) + COALESCE(1.0 / (60 + k.keyword_rank), 0.0) AS rrf_score
    FROM chunks c
    LEFT JOIN vector_search v ON c.chunk_id = v.chunk_id
    LEFT JOIN keyword_search k ON c.chunk_id = k.chunk_id
    JOIN documents d ON c.document_id = d.id
    WHERE v.chunk_id IS NOT NULL OR k.chunk_id IS NOT NULL
    ORDER BY rrf_score DESC
    LIMIT %s;
    """
    
    with conn.cursor() as cur:
        # Register pgvector type to handle list[float] to vector conversion for this connection
        from pgvector.psycopg2 import register_vector
        register_vector(conn)
        
        cur.execute(sql, (
            query_embedding, query_embedding, top_k, # Vector part
            query_text, query_text, query_text, top_k, # Keyword part
            top_k # Final limit
        ))
        rows = cur.fetchall()
        
    results = []
    for row in rows:
        results.append({
            "chunk_id": row[0],
            "content": row[1],
            "heading_path": row[2],
            "breadcrumb": row[3],
            "rrf_score": float(row[4]),
        })
    
    print(f"[Search] Hybrid search retrieved {len(results)} chunks.")
    return results


def rerank_results(query: str, results: List[Dict[str, Any]], top_k: int = RERANK_TOP_K) -> List[Dict[str, Any]]:
    """
    Reranks the retrieved chunks using a Cross-Encoder model.
    """
    if not results:
        return []
        
    documents = [res["content"] for res in results]
    
    print(f"[Search] Reranking {len(documents)} chunks...")
    
    # sentence_transformers CrossEncoder.predict takes a list of (query, document) tuples
    scores = _cross_encoder.predict([(query, doc) for doc in documents])
    
    for i, score in enumerate(scores):
        results[i]["rerank_score"] = float(score)

    results.sort(key=lambda x: x["rerank_score"], reverse=True)
    
    final_results = results[:top_k]
    print(f"[Search] Kept Top {len(final_results)} chunks after reranking.")
    return final_results
