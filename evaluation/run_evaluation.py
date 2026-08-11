"""
Evaluation Runner — orchestrates the full Phase 4 evaluation pipeline.

Usage:
    # Step 1 (one-time): Generate synthetic ground truth dataset (~9 min, 100 LLM calls)
    uv run python -m evaluation.run_evaluation --generate

    # Step 2: Run full evaluation (retrieval + LLM judge)
    uv run python -m evaluation.run_evaluation

    # Retrieval-only (faster, skips LLM judge)
    uv run python -m evaluation.run_evaluation --skip-llm-eval

    # Combined: generate + evaluate in one go
    uv run python -m evaluation.run_evaluation --generate --evaluate

    # Custom sample sizes
    uv run python -m evaluation.run_evaluation --n-chunks 50 --n-sample 15
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from retrieval.rag_base import RAGBase
from evaluation.rag_eval import RAGEvaluator, N_SAMPLE
from evaluation.qa_generator import DEFAULT_OUTPUT_PATH, N_CHUNKS, build_ground_truth_dataset
from evaluation.rate_limiter import RateLimiter
from evaluation.retrieval_eval import K_VALUES, RetrievalEvaluator
from ingestion.config import RETRIEVAL_TOP_K, RERANK_TOP_K

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
GROUND_TRUTH_PATH = DEFAULT_OUTPUT_PATH


# ── I/O Helpers ───────────────────────────────────────────────────────────────

def load_ground_truth(path: Path) -> list:
    """Load ground truth JSON from disk. Exits with error if file not found."""
    if not path.exists():
        logger.error(
            f"Ground truth not found at {path}. "
            "Run with --generate first to create it."
        )
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"[Runner] Loaded {len(data)} Q&A pairs from {path}")
    return data


# ── Pretty-print Tables ───────────────────────────────────────────────────────

def print_retrieval_table(retrieval_results: dict) -> None:
    """Print a formatted Hit Rate / MRR comparison table."""
    col_w = 22
    k_labels = [f"Hit@{k}" for k in K_VALUES] + [f"MRR@{k}" for k in K_VALUES]

    print("\n" + "═" * 80)
    print("  RETRIEVAL EVALUATION RESULTS")
    print("═" * 80)
    header = f"{'Strategy':<{col_w}}" + "".join(f"{lbl:>8}" for lbl in k_labels)
    print(header)
    print("─" * 80)

    for strategy, m in retrieval_results.items():
        row = f"{strategy:<{col_w}}"
        row += "".join(f"{m[f'hit_rate@{k}']:>8.3f}" for k in K_VALUES)
        row += "".join(f"{m[f'mrr@{k}']:>8.3f}" for k in K_VALUES)
        print(row)

    print("═" * 80)


def print_llm_table(llm_results: dict) -> None:
    """Print a formatted LLM judge results summary."""
    print("\n" + "═" * 50)
    print("  LLM QUALITY EVALUATION RESULTS")
    print("═" * 50)
    print(f"  Questions evaluated : {llm_results['n_evaluated']}")
    if llm_results.get("n_skipped"):
        print(f"  Skipped (API error) : {llm_results['n_skipped']}")
    print(f"  Avg Faithfulness    : {llm_results['avg_faithfulness']:.2f} / 5.0")
    print(f"  Avg Answer Relevance: {llm_results['avg_relevance']:.2f} / 5.0")
    print("═" * 50)


# ── Report Generation ─────────────────────────────────────────────────────────

def save_report(
    retrieval_results: dict,
    llm_results: dict,
    qa_pairs: list,
) -> None:
    """
    Persist evaluation results to JSON and Markdown in RESULTS_DIR.

    Files created:
      - evaluation/results/eval_report.json
      - evaluation/results/eval_report.md
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── JSON Report ──
    report = {
        "timestamp":            timestamp,
        "ground_truth_size":    len(qa_pairs),
        "retrieval_evaluation": {
            strategy: {k: v for k, v in metrics.items() if k != "ranks"}
            for strategy, metrics in retrieval_results.items()
        },
        "llm_evaluation": {
            k: v for k, v in llm_results.items() if k != "details"
        },
        "llm_evaluation_details": llm_results.get("details", []),
    }
    json_path = RESULTS_DIR / "eval_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ── Markdown Report ──
    md_path = RESULTS_DIR / "eval_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Evaluation Report\n\n")
        f.write(f"**Generated:** {timestamp}  \n")
        f.write(f"**Ground Truth Size:** {len(qa_pairs)} Q&A pairs\n\n")

        # Retrieval table
        f.write("## Retrieval Evaluation\n\n")
        header_cols = (
            ["Strategy"]
            + [f"Hit@{k}" for k in K_VALUES]
            + [f"MRR@{k}" for k in K_VALUES]
        )
        f.write("| " + " | ".join(header_cols) + " |\n")
        f.write("|" + "|".join(["---"] * len(header_cols)) + "|\n")
        for strategy, m in retrieval_results.items():
            row_vals = (
                [strategy]
                + [f"{m[f'hit_rate@{k}']:.3f}" for k in K_VALUES]
                + [f"{m[f'mrr@{k}']:.3f}" for k in K_VALUES]
            )
            f.write("| " + " | ".join(row_vals) + " |\n")

        # LLM quality table
        f.write("\n## LLM Quality Evaluation\n\n")
        f.write("| Metric | Score |\n|---|---|\n")
        f.write(f"| Avg Faithfulness    | {llm_results['avg_faithfulness']:.2f} / 5.0 |\n")
        f.write(f"| Avg Answer Relevance | {llm_results['avg_relevance']:.2f} / 5.0 |\n")
        f.write(f"| Samples evaluated   | {llm_results['n_evaluated']} |\n")

        # Per-sample details
        details = llm_results.get("details", [])
        if details:
            f.write("\n## Per-Sample LLM Judge Details\n\n")
            f.write("| # | Question | Faith. | Rel. | Reasoning |\n")
            f.write("|---|---|---|---|---|\n")
            for i, d in enumerate(details, start=1):
                q = d["question"][:70].replace("|", "\\|")
                r = d["reasoning"][:100].replace("|", "\\|")
                f.write(f"| {i} | {q}... | {d['faithfulness']} | {d['relevance']} | {r} |\n")

    logger.info(f"[Runner] Reports saved:\n  JSON → {json_path}\n  MD   → {md_path}")


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Startup OS RAG Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--generate", action="store_true",
        help="Generate synthetic ground truth dataset (runs LLM for each sampled chunk)",
    )
    parser.add_argument(
        "--evaluate", action="store_true",
        help="Run retrieval + LLM evaluation (default if no flag given)",
    )
    parser.add_argument(
        "--skip-llm-eval", action="store_true",
        help="Skip LLM judge evaluation — only compute retrieval metrics",
    )
    parser.add_argument(
        "--llm-only", action="store_true",
        help="Skip retrieval evaluation and only run LLM judge (uses cached retrieval results)",
    )
    parser.add_argument(
        "--n-chunks", type=int, default=N_CHUNKS, metavar="N",
        help=f"Chunks to sample for QA generation (default: {N_CHUNKS})",
    )
    parser.add_argument(
        "--n-sample", type=int, default=N_SAMPLE, metavar="N",
        help=f"Q&A pairs to evaluate with LLM judge (default: {N_SAMPLE})",
    )
    return parser.parse_args()


def main() -> None:
    """Main orchestration entry point."""
    args = parse_args()

    # Default: run --evaluate if no flag is given
    if not args.generate and not args.evaluate and not args.llm_only:
        args.evaluate = True

    # ── Phase 4A: Synthetic QA Generation ─────────────────────────────────────
    if args.generate:
        logger.info("=" * 60)
        logger.info("  PHASE 4A: Synthetic QA Generation")
        logger.info(f"  Sampling {args.n_chunks} chunks → {args.n_chunks * 3} Q&A pairs")
        logger.info(f"  Estimated time: ~{args.n_chunks // 12 + 1} minutes")
        logger.info("=" * 60)
        build_ground_truth_dataset(n_chunks=args.n_chunks, output_path=GROUND_TRUTH_PATH)

    # ── Phase 4B + 4C: Full Evaluation ────────────────────────────────────────
    if args.evaluate:
        qa_pairs = load_ground_truth(GROUND_TRUTH_PATH)

        logger.info("[Runner] Initializing RAGBase (cross-encoder loads once)...")
        rag = RAGBase()
        rate_limiter = RateLimiter(rpm=12)

        # Phase 4B: Retrieval Evaluation
        logger.info("=" * 60)
        logger.info("  PHASE 4B: Retrieval Evaluation")
        logger.info(f"  Questions: {len(qa_pairs)} | Strategies: 3 | K: {K_VALUES}")
        logger.info("=" * 60)
        retrieval_evaluator = RetrievalEvaluator(rag, top_k=RETRIEVAL_TOP_K, rerank_top_k=RERANK_TOP_K)
        retrieval_results = retrieval_evaluator.evaluate(qa_pairs)
        print_retrieval_table(retrieval_results)

        # Phase 4C: LLM Quality Evaluation (optional)
        llm_results = {
            "n_evaluated": 0, "n_skipped": 0,
            "avg_faithfulness": 0.0, "avg_relevance": 0.0,
            "details": [],
        }
        if not args.skip_llm_eval:
            logger.info("=" * 60)
            logger.info("  PHASE 4C: LLM Quality Evaluation")
            logger.info(f"  Sample: {args.n_sample} questions | Judge: Gemini-as-a-Judge")
            logger.info(f"  Estimated time: ~{args.n_sample // 12 + 1} minutes")
            logger.info("=" * 60)
            llm_evaluator = RAGEvaluator(rag, rate_limiter)
            llm_results = llm_evaluator.evaluate(qa_pairs, n_sample=args.n_sample)
            print_llm_table(llm_results)

        # Save reports
        save_report(retrieval_results, llm_results, qa_pairs)

        logger.info("\n[Runner] ✅ Evaluation complete!")

    # ── Phase 4C only: LLM Judge using cached retrieval results ───────────────
    if args.llm_only:
        import json as _json
        qa_pairs = load_ground_truth(GROUND_TRUTH_PATH)

        logger.info("[Runner] --llm-only mode: skipping retrieval eval, using cached results.")
        cached_report = RESULTS_DIR / "eval_report.json"
        if cached_report.exists():
            with open(cached_report) as f:
                cached = _json.load(f)
            retrieval_results = cached.get("retrieval_evaluation", {})
            logger.info("[Runner] Loaded cached retrieval results from eval_report.json")
        else:
            retrieval_results = {}
            logger.warning("[Runner] No cached retrieval results found. Save report will have empty retrieval section.")

        logger.info("[Runner] Initializing RAGBase (cross-encoder loads once)...")
        rag = RAGBase()
        rate_limiter = RateLimiter(rpm=12)

        logger.info("=" * 60)
        logger.info("  PHASE 4C: LLM Quality Evaluation (llm-only mode)")
        logger.info(f"  Sample: {args.n_sample} questions | Judge: Gemini-as-a-Judge")
        logger.info(f"  Estimated time: ~{args.n_sample // 12 + 1} minutes")
        logger.info("=" * 60)
        llm_evaluator = RAGEvaluator(rag, rate_limiter)
        llm_results = llm_evaluator.evaluate(qa_pairs, n_sample=args.n_sample)
        print_llm_table(llm_results)

        # Append LLM results into existing report without overwriting retrieval scores
        save_report(retrieval_results, llm_results, qa_pairs)
        logger.info("\n[Runner] ✅ LLM evaluation complete!")


if __name__ == "__main__":
    main()
