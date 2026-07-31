"""
Retrieval Evaluator — measures Hit Rate@K and MRR@K across three strategies:
  1. vector_only       — pgvector cosine similarity (no keyword search)
  2. hybrid            — Vector + BM25 full-text + Reciprocal Rank Fusion
  3. hybrid_reranker   — Hybrid + Cross-Encoder reranking

For each Q&A pair in the ground truth dataset, the evaluator checks whether
the source_chunk_id (the chunk used to generate the question) appears in
the top-K results returned by each strategy.
"""
import logging
from typing import Any, Dict, List, Optional

from pgvector.psycopg2 import register_vector

from ingestion.embedder import embed_query
from ingestion.loader import get_connection
from retrieval.rag_base import RAGBase

logger = logging.getLogger(__name__)

# K values for which Hit Rate and MRR are computed
K_VALUES: List[int] = [1, 3, 5, 10]


# ── Vector-only Search ────────────────────────────────────────────────────────

def vector_only_search(
    conn,
    query_embedding: List[float],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Pure pgvector cosine similarity search — no BM25, no RRF.

    Args:
        conn: Active psycopg2 database connection.
        query_embedding: Dense vector representation of the query.
        top_k: Number of results to return.

    Returns:
        List of chunk dicts ordered by descending cosine similarity.
    """
    sql = """
        SELECT
            c.chunk_id,
            c.content,
            c.heading_path,
            d.breadcrumb,
            1 - (c.embedding <=> %s::vector) AS cosine_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s;
    """
    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute(sql, (query_embedding, query_embedding, top_k))
        rows = cur.fetchall()

    return [
        {
            "chunk_id":     row[0],
            "content":      row[1],
            "heading_path": row[2],
            "breadcrumb":   row[3],
            "score":        float(row[4]),
        }
        for row in rows
    ]


# ── Metric Helpers ────────────────────────────────────────────────────────────

def get_rank(source_chunk_id: str, results: List[Dict[str, Any]]) -> Optional[int]:
    """
    Return the 1-indexed rank of source_chunk_id in results, or None if absent.
    """
    for i, r in enumerate(results):
        if r["chunk_id"] == source_chunk_id:
            return i + 1
    return None


def hit_rate_at_k(ranks: List[Optional[int]], k: int) -> float:
    """
    Hit Rate@K — fraction of queries where the source chunk appears in top-K.

    Args:
        ranks: List of ranks (1-indexed) or None for not-found entries.
        k: Cutoff threshold.

    Returns:
        Float in [0.0, 1.0].
    """
    if not ranks:
        return 0.0
    hits = sum(1 for r in ranks if r is not None and r <= k)
    return hits / len(ranks)


def mrr_at_k(ranks: List[Optional[int]], k: int) -> float:
    """
    Mean Reciprocal Rank@K — average of 1/rank (0 if rank > k or not found).

    Args:
        ranks: List of ranks (1-indexed) or None for not-found entries.
        k: Cutoff threshold.

    Returns:
        Float in [0.0, 1.0].
    """
    if not ranks:
        return 0.0
    reciprocals = [1.0 / r if r is not None and r <= k else 0.0 for r in ranks]
    return sum(reciprocals) / len(reciprocals)


# ── Evaluator Class ───────────────────────────────────────────────────────────

class RetrievalEvaluator:
    """
    Evaluates three retrieval strategies on a ground truth Q&A dataset.

    Uses RAGBase for hybrid search and cross-encoder reranking.
    Implements vector_only search as a standalone SQL query for fair comparison.
    """

    def __init__(self, rag: RAGBase, top_k: int = 20, rerank_top_k: int = 10) -> None:
        """
        Args:
            rag: Initialized RAGBase instance (shared to avoid reloading cross-encoder).
            top_k: Number of candidates retrieved per strategy (vector + hybrid arms).
            rerank_top_k: Number of chunks kept after cross-encoder reranking.
                          Should be >= max(K_VALUES) for fair metric computation.
        """
        self.rag = rag
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k

    def evaluate(self, qa_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run all three retrieval strategies on every Q&A pair and compute metrics.

        For each question:
          1. Embed the question (shared across all strategies)
          2. Run vector_only, hybrid, and hybrid_reranker searches
          3. Record the rank of source_chunk_id in each result list

        Args:
            qa_pairs: List of dicts with 'question' and 'source_chunk_id' keys.

        Returns:
            Dict mapping strategy name → metric dict with hit_rate@K and mrr@K values.
        """
        ranks: Dict[str, List[Optional[int]]] = {
            "vector_only":       [],
            "hybrid":            [],
            "hybrid_reranker":   [],
        }

        total = len(qa_pairs)
        logger.info(f"[RetrievalEval] Starting evaluation on {total} questions (3 strategies)...")

        for i, qa in enumerate(qa_pairs, start=1):
            question        = qa["question"]
            source_chunk_id = qa["source_chunk_id"]

            logger.info(f"[RetrievalEval] [{i}/{total}] '{question[:70]}...'")

            # Embed once — reused by all three strategies
            query_embedding = embed_query(question)

            conn = get_connection()
            try:
                # --- Strategy 1: Vector-only ---
                v_results = vector_only_search(conn, query_embedding, top_k=self.top_k)
                ranks["vector_only"].append(get_rank(source_chunk_id, v_results))

                # --- Strategy 2: Hybrid (Vector + BM25 + RRF) ---
                h_results = self.rag.hybrid_search(
                    conn, question, query_embedding, top_k=self.top_k
                )
                ranks["hybrid"].append(get_rank(source_chunk_id, h_results))

                # --- Strategy 3: Hybrid + Cross-Encoder Reranker ---
                # rerank_top_k=self.rerank_top_k (>= 10) for fair metric computation at K=10
                r_results = self.rag.rerank_results(
                    question, list(h_results), top_k=self.rerank_top_k
                )
                ranks["hybrid_reranker"].append(get_rank(source_chunk_id, r_results))

            finally:
                conn.close()

        # Compute metrics for each strategy and each K value
        results: Dict[str, Any] = {}
        for strategy, strategy_ranks in ranks.items():
            n_found = sum(1 for r in strategy_ranks if r is not None)
            results[strategy] = {
                "n_questions": len(strategy_ranks),
                "n_found":     n_found,
                "ranks":       strategy_ranks,
                **{f"hit_rate@{k}": hit_rate_at_k(strategy_ranks, k) for k in K_VALUES},
                **{f"mrr@{k}":      mrr_at_k(strategy_ranks, k)      for k in K_VALUES},
            }
            logger.info(
                f"[RetrievalEval] {strategy}: found={n_found}/{len(strategy_ranks)}, "
                f"Hit@5={results[strategy]['hit_rate@5']:.3f}, "
                f"MRR@10={results[strategy]['mrr@10']:.3f}"
            )

        logger.info("[RetrievalEval] Evaluation complete.")
        return results
