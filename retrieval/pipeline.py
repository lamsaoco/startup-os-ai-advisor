"""
RAG Pipeline — Thin backward-compatibility wrapper around RAGBase.

Prefer importing RAGBase directly for new code.
"""
from typing import Dict, Any

from retrieval.rag_base import RAGBase

# Module-level singleton to avoid reloading the cross-encoder on every call
_rag = RAGBase()


def run_rag_pipeline(user_query: str) -> Dict[str, Any]:
    """
    Execute the full RAG pipeline.

    Delegates to RAGBase.run(). Kept for backward compatibility.

    Args:
        user_query: The raw query string from the user.

    Returns:
        Dict with keys: user_query, rewritten_query, retrieved_chunks,
        answer, latency_seconds.
    """
    return _rag.run(user_query)
