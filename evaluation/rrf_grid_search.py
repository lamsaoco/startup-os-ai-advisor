"""
RRF Grid Search — systematically tests different combinations of the two
RRF hyper-parameters to find the configuration that maximises Hit@5:

  * k         — smoothing constant in the RRF denominator  1/(k + rank)
  * w_vector  — weight assigned to the vector arm (w_bm25 = 1 - w_vector)

Strategy: Only evaluate the "hybrid" strategy (no reranker) because:
  - It isolates the RRF effect cleanly.
  - It is ≈30x faster than running the cross-encoder on every config.
  - The reranker only reorders the top-K pool produced by hybrid search;
    improving hybrid retrieval also improves reranker input quality.

Embeddings are precomputed once and cached in RAM to avoid redundant GPU/CPU work.
"""

import json
import logging
import os
import sys
import time
from itertools import product
from typing import Any, Dict, List, Optional

# ── Path setup so script can be run as a module or directly ──────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from pgvector.psycopg2 import register_vector

from ingestion.embedder import embed_query
from ingestion.loader import get_connection
from ingestion.config import RETRIEVAL_TOP_K

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Ground truth ─────────────────────────────────────────────────────────────
GROUND_TRUTH_PATH = os.path.join(os.path.dirname(__file__), "data", "ground_truth.json")

# ── Grid to search ────────────────────────────────────────────────────────────
K_VALUES_RRF   = [5, 10, 20, 40, 60]          # RRF smoothing constant
W_VECTOR_VALS  = [0.5, 0.6, 0.75, 0.85, 0.9, 1.0]  # weight for vector arm
TOP_K_RETRIEVE = RETRIEVAL_TOP_K               # number of results per query

# Metric K values to display in the report
METRIC_K = [1, 3, 5, 10]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_qa_pairs(path: str) -> List[Dict[str, Any]]:
    """Load ground-truth QA pairs from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    # Accept both a bare list and {"qa_pairs": [...]}
    if isinstance(data, list):
        return data
    return data.get("qa_pairs", [])


def hit_rate_at_k(ranks: List[Optional[int]], k: int) -> float:
    """Fraction of queries where the correct chunk appears in top-K."""
    hits = sum(1 for r in ranks if r is not None and r <= k)
    return hits / len(ranks) if ranks else 0.0


def mrr_at_k(ranks: List[Optional[int]], k: int) -> float:
    """Mean Reciprocal Rank at K."""
    rr_sum = sum(1.0 / r for r in ranks if r is not None and r <= k)
    return rr_sum / len(ranks) if ranks else 0.0


def get_rank(source_chunk_id: str, results: List[Dict]) -> Optional[int]:
    """Return 1-based rank of source_chunk_id in results, or None if absent."""
    for i, res in enumerate(results, start=1):
        if res["chunk_id"] == source_chunk_id:
            return i
    return None


def hybrid_search_parametric(
    conn,
    query_text: str,
    query_embedding: List[float],
    top_k: int,
    k_rrf: float,
    w_vector: float,
) -> List[Dict[str, Any]]:
    """
    Parameterised hybrid search — k_rrf and w_vector are injected as SQL params.

    Args:
        conn:            psycopg2 connection.
        query_text:      BM25 query string.
        query_embedding: Dense embedding of the query.
        top_k:           Number of results to return.
        k_rrf:           RRF smoothing constant.
        w_vector:        Weight for the vector arm (0-1). BM25 weight = 1 - w_vector.

    Returns:
        List of chunk dicts ordered by descending RRF score.
    """
    w_bm25 = 1.0 - w_vector
    sql = f"""
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
        ({w_vector} * COALESCE(1.0 / ({k_rrf} + v.vector_rank), 0.0)) +
        ({w_bm25} * COALESCE(1.0 / ({k_rrf} + k.keyword_rank), 0.0)) AS rrf_score
    FROM chunks c
    LEFT JOIN vector_search v ON c.chunk_id = v.chunk_id
    LEFT JOIN keyword_search k ON c.chunk_id = k.chunk_id
    JOIN documents d ON c.document_id = d.id
    WHERE v.chunk_id IS NOT NULL OR k.chunk_id IS NOT NULL
    ORDER BY rrf_score DESC
    LIMIT %s;
    """
    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute(sql, (
            query_embedding, query_embedding, top_k,       # vector arm
            query_text, query_text, query_text, top_k,    # keyword arm
            top_k,                                         # final LIMIT
        ))
        rows = cur.fetchall()

    return [
        {
            "chunk_id":     row[0],
            "content":      row[1],
            "heading_path": row[2],
            "breadcrumb":   row[3],
            "rrf_score":    float(row[4]),
        }
        for row in rows
    ]


# ── Main Grid Search ──────────────────────────────────────────────────────────

def run_grid_search():
    # 1. Load ground truth
    logger.info(f"Loading ground truth from {GROUND_TRUTH_PATH}…")
    qa_pairs = load_qa_pairs(GROUND_TRUTH_PATH)
    logger.info(f"Loaded {len(qa_pairs)} QA pairs.")

    # 2. Precompute embeddings for all questions (done once, reused across all configs)
    logger.info("Precomputing query embeddings (this may take a minute)…")
    t0 = time.time()
    embeddings = []
    for i, qa in enumerate(qa_pairs, start=1):
        embeddings.append(embed_query(qa["question"]))
        if i % 50 == 0:
            logger.info(f"  Embedded {i}/{len(qa_pairs)} queries…")
    elapsed = time.time() - t0
    logger.info(f"Embeddings ready in {elapsed:.1f}s.")

    # 3. Grid search
    configs = list(product(K_VALUES_RRF, W_VECTOR_VALS))
    total_configs = len(configs)
    logger.info(f"\nRunning grid search over {total_configs} configurations…\n")

    results_table = []

    for cfg_idx, (k_rrf, w_vector) in enumerate(configs, start=1):
        w_bm25 = round(1.0 - w_vector, 2)
        label = f"k={k_rrf:3d} | w_vec={w_vector:.2f} | w_bm25={w_bm25:.2f}"
        logger.info(f"[{cfg_idx:2d}/{total_configs}] Testing: {label}")

        ranks: List[Optional[int]] = []
        t_start = time.time()

        for qa, emb in zip(qa_pairs, embeddings):
            conn = get_connection()
            try:
                hits = hybrid_search_parametric(
                    conn,
                    query_text=qa["question"],
                    query_embedding=emb,
                    top_k=TOP_K_RETRIEVE,
                    k_rrf=k_rrf,
                    w_vector=w_vector,
                )
                ranks.append(get_rank(qa["source_chunk_id"], hits))
            finally:
                conn.close()

        elapsed_cfg = time.time() - t_start

        row = {
            "k_rrf":    k_rrf,
            "w_vector": w_vector,
            "w_bm25":   w_bm25,
            "hit@1":    hit_rate_at_k(ranks, 1),
            "hit@3":    hit_rate_at_k(ranks, 3),
            "hit@5":    hit_rate_at_k(ranks, 5),
            "hit@10":   hit_rate_at_k(ranks, 10),
            "mrr@5":    mrr_at_k(ranks, 5),
            "mrr@10":   mrr_at_k(ranks, 10),
            "time_s":   round(elapsed_cfg, 1),
        }
        results_table.append(row)
        logger.info(
            f"    → Hit@1={row['hit@1']:.3f} | Hit@3={row['hit@3']:.3f} "
            f"| Hit@5={row['hit@5']:.3f} | Hit@10={row['hit@10']:.3f} "
            f"| MRR@5={row['mrr@5']:.3f} ({elapsed_cfg:.0f}s)"
        )

    # 4. Print full sorted results table
    results_table.sort(key=lambda r: (-r["hit@5"], -r["hit@1"], -r["mrr@5"]))

    header = f"\n{'Rank':>4} | {'k_rrf':>5} | {'w_vec':>5} | {'w_bm25':>6} | {'Hit@1':>6} | {'Hit@3':>6} | {'Hit@5':>6} | {'Hit@10':>7} | {'MRR@5':>6} | {'MRR@10':>7}"
    divider = "-" * len(header)
    print("\n" + "=" * len(header))
    print("  RRF GRID SEARCH RESULTS (sorted by Hit@5 DESC, then Hit@1 DESC)")
    print("=" * len(header))
    print(header)
    print(divider)
    for rank, row in enumerate(results_table, start=1):
        print(
            f"{rank:>4} | {row['k_rrf']:>5} | {row['w_vector']:>5.2f} | {row['w_bm25']:>6.2f} | "
            f"{row['hit@1']:>6.3f} | {row['hit@3']:>6.3f} | {row['hit@5']:>6.3f} | {row['hit@10']:>7.3f} | "
            f"{row['mrr@5']:>6.3f} | {row['mrr@10']:>7.3f}"
        )
    print("=" * len(header))

    # 5. Save results to JSON
    out_path = os.path.join(os.path.dirname(__file__), "results", "rrf_grid_search.json")
    with open(out_path, "w") as f:
        json.dump(results_table, f, indent=2)
    logger.info(f"\nFull results saved → {out_path}")

    best = results_table[0]
    logger.info(
        f"\n🏆 Best config: k_rrf={best['k_rrf']}, w_vector={best['w_vector']}, "
        f"Hit@5={best['hit@5']:.3f}, Hit@1={best['hit@1']:.3f}, MRR@5={best['mrr@5']:.3f}"
    )


if __name__ == "__main__":
    run_grid_search()
