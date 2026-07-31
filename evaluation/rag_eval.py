"""
LLM Quality Evaluator — Gemini-as-a-Judge for RAG answer quality.

Samples N questions from the ground truth dataset, runs the full RAG pipeline
to generate answers, then uses Gemini as an impartial judge to score each
answer on two dimensions:
  - Faithfulness (0–5): Is the answer grounded in the retrieved context?
  - Answer Relevance (0–5): Does the answer actually address the question?
"""
import json
import logging
import random
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ingestion.config import CHAT_MODEL, GEMINI_API_KEY, GEMINI_BASE_URL
from retrieval.rag_base import RAGBase
from evaluation.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

N_SAMPLE: int = 30  # Number of Q&A pairs to evaluate with LLM judge

# ── Judge Prompt ──────────────────────────────────────────────────────────────
_JUDGE_SYSTEM_PROMPT = """You are an impartial judge evaluating the quality of a RAG (Retrieval-Augmented Generation) system.

You will be given:
1. A user question
2. The retrieved context chunks used to answer it
3. The generated answer

Evaluate the answer on TWO dimensions:

FAITHFULNESS (0-5): Does the answer stay faithful to the provided context?
- 5: Every claim is directly supported by the context; no hallucinations
- 4: Almost all claims supported; minor extrapolation acceptable
- 3: Most claims supported but some unsupported statements present
- 2: Significant unsupported or fabricated claims
- 1: Mostly hallucinated; little grounding in context
- 0: Completely fabricated; ignores context entirely

RELEVANCE (0-5): Does the answer actually address the user's question?
- 5: Directly and completely answers the question
- 4: Mostly answers the question with minor gaps
- 3: Partially answers the question
- 2: Tangentially related but misses the main point
- 1: Barely relevant to the question
- 0: Completely off-topic

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{"faithfulness": <integer 0-5>, "relevance": <integer 0-5>, "reasoning": "<one concise sentence>"}"""


# ── Judge Logic ───────────────────────────────────────────────────────────────

def _build_judge_user_message(
    question: str,
    context_chunks: List[Dict[str, Any]],
    answer: str,
) -> str:
    """Format the question, context, and answer into a judge prompt."""
    context_text = "\n\n".join(
        f"[Source {i + 1}] {c.get('breadcrumb', '')} > {c.get('heading_path', '')}\n"
        f"{c.get('content', '')}"
        for i, c in enumerate(context_chunks)
    )
    return (
        f"QUESTION:\n{question}\n\n"
        f"RETRIEVED CONTEXT:\n{context_text}\n\n"
        f"GENERATED ANSWER:\n{answer}"
    )


def _parse_judge_response(raw: str) -> Optional[Dict[str, Any]]:
    """
    Parse the LLM judge's JSON response.

    Returns a dict with faithfulness, relevance, reasoning, or None on failure.
    """
    try:
        # Strip markdown code fences if present
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        scores = json.loads(cleaned)
        return {
            "faithfulness": int(scores["faithfulness"]),
            "relevance":    int(scores["relevance"]),
            "reasoning":    str(scores.get("reasoning", "")),
        }
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.error(f"[RAGEval] Failed to parse judge response: {exc}. Raw: {raw[:200]}")
        return None


# ── Evaluator Class ───────────────────────────────────────────────────────────

class RAGEvaluator:
    """
    Gemini-as-a-Judge evaluator for RAG answer quality.

    Uses the same Gemini model as the RAG pipeline itself to evaluate
    Faithfulness and Answer Relevance on a sampled subset of Q&A pairs.
    """

    def __init__(self, rag: RAGBase, rate_limiter: RateLimiter) -> None:
        """
        Args:
            rag: Initialized RAGBase instance to generate answers.
            rate_limiter: Shared RateLimiter for judge API calls.
        """
        self.rag = rag
        self.rate_limiter = rate_limiter
        self._llm_client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)

    def _judge_single(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        answer: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Call Gemini-as-a-Judge for a single Q&A pair with rate limiting.

        Args:
            question: The original user question.
            context_chunks: Retrieved chunks used to generate the answer.
            answer: The LLM-generated answer to evaluate.

        Returns:
            Dict with faithfulness, relevance, reasoning keys, or None on failure.
        """
        user_message = _build_judge_user_message(question, context_chunks, answer)

        def _call() -> str:
            response = self._llm_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.1,  # Low temperature for consistent scoring
            )
            return response.choices[0].message.content.strip()

        try:
            raw = self.rate_limiter.call_with_retry(_call)
            return _parse_judge_response(raw)
        except Exception as exc:
            logger.error(f"[RAGEval] Judge API call failed: {exc}")
            return None

    def evaluate(
        self,
        qa_pairs: List[Dict[str, Any]],
        n_sample: int = N_SAMPLE,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Evaluate answer quality on a random sample of Q&A pairs.

        Pipeline per question:
          1. Run full RAG pipeline → answer + retrieved_chunks
          2. Call Gemini-as-a-Judge with rate limiting → faithfulness + relevance
          3. Aggregate results

        Args:
            qa_pairs: Full ground truth dataset.
            n_sample: Number of pairs to evaluate (randomly sampled).
            seed: Random seed for reproducible sampling.

        Returns:
            Dict with avg_faithfulness, avg_relevance, n_evaluated, and per-sample details.
        """
        random.seed(seed)
        sample = random.sample(qa_pairs, min(n_sample, len(qa_pairs)))
        n = len(sample)

        logger.info(f"[RAGEval] Evaluating {n} questions with Gemini-as-a-Judge...")

        details: List[Dict[str, Any]] = []
        skipped = 0

        for i, qa in enumerate(sample, start=1):
            question = qa["question"]
            logger.info(f"[RAGEval] [{i}/{n}] Running RAG for: '{question[:60]}...'")

            # Step 1: Generate answer via full RAG pipeline (no rate limit — retrieval is local)
            rag_result = self.rag.run(question)
            answer          = rag_result["answer"]
            context_chunks  = rag_result["retrieved_chunks"]

            # Step 2: Judge the answer (rate-limited LLM call)
            logger.info(f"[RAGEval] [{i}/{n}] Judging answer...")
            scores = self._judge_single(question, context_chunks, answer)

            if scores is None:
                skipped += 1
                logger.warning(f"[RAGEval] [{i}/{n}] Judge failed — skipping.")
                continue

            details.append({
                "question":          question,
                "answer":            answer,
                "faithfulness":      scores["faithfulness"],
                "relevance":         scores["relevance"],
                "reasoning":         scores["reasoning"],
                "source_chunk_id":   qa["source_chunk_id"],
                "source_breadcrumb": qa.get("source_breadcrumb", ""),
            })
            logger.info(
                f"[RAGEval] [{i}/{n}] Faithfulness={scores['faithfulness']}/5, "
                f"Relevance={scores['relevance']}/5 — {scores['reasoning']}"
            )

        if not details:
            logger.error("[RAGEval] All judge calls failed — no results to aggregate.")
            return {"n_evaluated": 0, "avg_faithfulness": 0.0, "avg_relevance": 0.0, "details": []}

        avg_faithfulness = sum(r["faithfulness"] for r in details) / len(details)
        avg_relevance    = sum(r["relevance"]    for r in details) / len(details)

        logger.info(
            f"[RAGEval] Done. Evaluated={len(details)}, Skipped={skipped}. "
            f"Avg Faithfulness={avg_faithfulness:.2f}/5, Avg Relevance={avg_relevance:.2f}/5"
        )

        return {
            "n_evaluated":       len(details),
            "n_skipped":         skipped,
            "avg_faithfulness":  round(avg_faithfulness, 3),
            "avg_relevance":     round(avg_relevance, 3),
            "details":           details,
        }
