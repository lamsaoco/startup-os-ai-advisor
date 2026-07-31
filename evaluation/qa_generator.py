"""
Synthetic QA Generator for ground truth dataset construction.

Samples representative chunks from the database (stratified by document),
then uses Gemini to generate 3 diverse questions per chunk.
The resulting Q&A pairs are saved to evaluation/data/ground_truth.json
and serve as the ground truth for retrieval and LLM evaluation.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ingestion.config import CHAT_MODEL, GEMINI_API_KEY, GEMINI_BASE_URL
from ingestion.loader import get_connection
from evaluation.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_OUTPUT_PATH = Path(__file__).parent / "data" / "ground_truth.json"
N_CHUNKS: int = 100          # Number of chunks to sample
MIN_TOKENS: int = 80         # Minimum token count to include a chunk
QUESTIONS_PER_CHUNK: int = 3  # Questions to generate per chunk

# ── LLM Prompt ────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert evaluator for a RAG system about startup management and HR.

Given an excerpt from a startup management handbook, generate exactly 3 diverse questions
that this text DIRECTLY and COMPLETELY answers.

Requirements:
- Q1: Direct factual question (e.g., "What is X?" or "What are the steps for Y?")
- Q2: Paraphrase with different wording (same intent, different phrasing)
- Q3: Scenario-based or "how-to" question (e.g., "How should a founder handle X when...?")

Rules:
- Each question must be answerable ONLY from the provided text, not general knowledge
- Questions must be specific enough to uniquely point to this passage
- Do NOT reference "the text", "the excerpt", or "the passage" in the questions
- Return ONLY a valid JSON array with exactly 3 strings — no explanation, no markdown

Example output:
["What is the recommended process for performance reviews?", "How should managers structure evaluation meetings?", "As a startup founder with 20 employees, what steps should I follow to set up performance reviews?"]"""


# ── DB Sampling ───────────────────────────────────────────────────────────────

def sample_chunks(conn, n: int = N_CHUNKS, min_tokens: int = MIN_TOKENS) -> List[Dict[str, Any]]:
    """
    Sample n chunks using stratified sampling across documents.

    First selects one chunk per document (stratified), then fills remaining
    slots with random chunks if needed. Filters chunks below min_tokens.

    Args:
        conn: Active psycopg2 database connection.
        n: Total number of chunks to sample.
        min_tokens: Minimum token count threshold.

    Returns:
        List of chunk dicts with keys: chunk_id, document_id, content,
        heading_path, token_count, breadcrumb.
    """
    # First pass: one random chunk per document
    sql_stratified = """
        SELECT DISTINCT ON (c.document_id)
            c.chunk_id,
            c.document_id,
            c.content,
            c.heading_path,
            c.token_count,
            d.breadcrumb
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.token_count >= %s
        ORDER BY c.document_id, RANDOM()
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql_stratified, (min_tokens, n))
        rows = cur.fetchall()

    sampled = [_row_to_dict(r) for r in rows]

    # Second pass: fill remaining slots with random chunks (if stratified gave fewer than n)
    if len(sampled) < n:
        existing_ids = [c["chunk_id"] for c in sampled]
        sql_fill = """
            SELECT c.chunk_id, c.document_id, c.content, c.heading_path, c.token_count, d.breadcrumb
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.token_count >= %s
              AND c.chunk_id <> ALL(%s::text[])
            ORDER BY RANDOM()
            LIMIT %s;
        """
        with conn.cursor() as cur:
            cur.execute(sql_fill, (min_tokens, existing_ids, n - len(sampled)))
            rows = cur.fetchall()
        sampled.extend(_row_to_dict(r) for r in rows)

    logger.info(f"[QAGenerator] Sampled {len(sampled)} chunks (n={n}, min_tokens={min_tokens})")
    return sampled[:n]


def _row_to_dict(row) -> Dict[str, Any]:
    """Convert a DB row tuple to a chunk dict."""
    return {
        "chunk_id":     row[0],
        "document_id":  row[1],
        "content":      row[2],
        "heading_path": row[3],
        "token_count":  row[4],
        "breadcrumb":   row[5],
    }


# ── Question Generation ────────────────────────────────────────────────────────

def generate_questions_for_chunk(
    chunk: Dict[str, Any],
    llm_client: OpenAI,
    rate_limiter: RateLimiter,
) -> Optional[List[str]]:
    """
    Generate QUESTIONS_PER_CHUNK questions for a single chunk using the LLM.

    Args:
        chunk: Chunk dict containing at minimum a 'content' key.
        llm_client: Initialized OpenAI-compatible client.
        rate_limiter: RateLimiter instance to throttle API calls.

    Returns:
        List of question strings, or None if generation fails.
    """
    user_message = f"Handbook excerpt:\n\n{chunk['content']}"

    def _call() -> str:
        response = llm_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    try:
        raw = rate_limiter.call_with_retry(_call)
        questions = json.loads(raw)
        if isinstance(questions, list) and len(questions) == QUESTIONS_PER_CHUNK:
            return [str(q).strip() for q in questions]
        logger.warning(
            f"[QAGenerator] Unexpected format for chunk {chunk['chunk_id'][:8]}: {raw[:120]}"
        )
        return None
    except json.JSONDecodeError as exc:
        logger.error(f"[QAGenerator] JSON parse error for chunk {chunk['chunk_id'][:8]}: {exc}")
        return None
    except Exception as exc:
        logger.error(f"[QAGenerator] Failed for chunk {chunk['chunk_id'][:8]}: {exc}")
        return None


# ── Main Entry Point ───────────────────────────────────────────────────────────

def build_ground_truth_dataset(
    n_chunks: int = N_CHUNKS,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> List[Dict[str, Any]]:
    """
    Build and persist the synthetic Q&A ground truth dataset.

    Pipeline:
      1. Sample n_chunks representative chunks from the DB
      2. Generate QUESTIONS_PER_CHUNK questions per chunk via Gemini
      3. Save results to output_path as JSON

    Args:
        n_chunks: Number of chunks to sample.
        output_path: File path to write the ground truth JSON.

    Returns:
        List of Q&A pair dicts with keys: question, source_chunk_id,
        source_document_id, source_breadcrumb, source_heading_path, source_content.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    llm_client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
    rate_limiter = RateLimiter(rpm=12)

    conn = get_connection()
    try:
        chunks = sample_chunks(conn, n=n_chunks)
    finally:
        conn.close()

    logger.info(
        f"[QAGenerator] Generating {QUESTIONS_PER_CHUNK} questions for each of "
        f"{len(chunks)} chunks (~{len(chunks)} API calls, ~{len(chunks) // 12 + 1} min)..."
    )

    qa_pairs: List[Dict[str, Any]] = []
    failed = 0

    for i, chunk in enumerate(chunks, start=1):
        questions = generate_questions_for_chunk(chunk, llm_client, rate_limiter)
        if questions is None:
            failed += 1
            logger.warning(f"[QAGenerator] [{i}/{len(chunks)}] FAILED — skipping chunk {chunk['chunk_id'][:8]}")
            continue

        for q in questions:
            qa_pairs.append({
                "question":           q,
                "source_chunk_id":    chunk["chunk_id"],
                "source_document_id": chunk["document_id"],
                "source_breadcrumb":  chunk["breadcrumb"],
                "source_heading_path": chunk["heading_path"],
                "source_content":     chunk["content"],
            })

        logger.info(
            f"[QAGenerator] [{i}/{len(chunks)}] chunk={chunk['chunk_id'][:8]}... "
            f"| {chunk['token_count']} tokens | {len(questions)} questions generated"
        )

    logger.info(
        f"[QAGenerator] Complete: {len(qa_pairs)} Q&A pairs "
        f"({len(chunks) - failed}/{len(chunks)} chunks succeeded, {failed} failed)."
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
    logger.info(f"[QAGenerator] Saved to {output_path}")

    return qa_pairs
