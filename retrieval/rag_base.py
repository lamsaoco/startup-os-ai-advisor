"""
RAGBase — Unified class encapsulating the full Retrieval-Augmented Generation pipeline.

Combines: Query Rewriting, Embedding, Hybrid Search (Vector + BM25 + RRF),
Cross-Encoder Reranking, and LLM Answer Generation.
"""
import time
from typing import List, Dict, Any

from openai import OpenAI
from sentence_transformers import CrossEncoder

from ingestion.config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    CHAT_MODEL,
    RETRIEVAL_TOP_K,
    RERANK_TOP_K,
    CROSS_ENCODER_MODEL,
)
from ingestion.embedder import embed_query
from ingestion.loader import get_connection


class RAGBase:
    """
    Unified RAG pipeline class that encapsulates all retrieval and generation steps:
      1. Query Rewriting  (LLM)
      2. Query Embedding  (local ONNX model)
      3. Hybrid Search    (pgvector cosine + BM25 full-text, fused via RRF)
      4. Reranking        (Cross-Encoder)
      5. Answer Generation (LLM)
    """

    def __init__(self, use_reranker: bool = True) -> None:
        """Initialize the LLM client and conditionally load the Cross-Encoder."""
        # OpenAI-compatible client pointed at Gemini endpoint
        self._llm_client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url=GEMINI_BASE_URL,
        )
        self.use_reranker = use_reranker
        if self.use_reranker:
            # Cross-Encoder loaded once at startup; uses HF_HOME for cache
            self._cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
            print(f"[RAGBase] Initialized with Reranker={CROSS_ENCODER_MODEL}")
        else:
            self._cross_encoder = None
            print("[RAGBase] Initialized without Reranker (Fast Mode)")

    # ------------------------------------------------------------------
    # Step 1 — Query Rewriting
    # ------------------------------------------------------------------

    def rewrite_query(self, user_query: str) -> str:
        """
        Rewrite the user query to expand synonyms, fix typos,
        and improve both vector and keyword retrieval coverage.

        Args:
            user_query: The original raw query from the user.

        Returns:
            A semantically expanded query string.
        """
        system_prompt = (
            "You are an expert HR and Startup Operations advisor. "
            "Your task is to rewrite the user's query to optimize it for a vector search "
            "and keyword search engine. "
            "Expand abbreviations (e.g., 'esop' -> 'Employee Stock Ownership Plan'), "
            "add relevant synonyms, and formulate a clear, comprehensive search query. "
            "Do NOT answer the query. Just provide the rewritten query."
        )

        print(f"[RAGBase] Rewriting query: '{user_query}'")
        response = self._llm_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Original query: {user_query}"},
            ],
            temperature=0.3,
        )
        rewritten = response.choices[0].message.content.strip()
        print(f"[RAGBase] Rewritten to: '{rewritten}'")
        return rewritten

    # ------------------------------------------------------------------
    # Step 2 — Hybrid Search (Vector + BM25 via RRF)
    # ------------------------------------------------------------------

    def hybrid_search(
        self,
        conn,
        query_text: str,
        query_embedding: List[float],
        top_k: int = RETRIEVAL_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Execute Hybrid Search combining pgvector cosine similarity and
        BM25 full-text search, fused via Reciprocal Rank Fusion (RRF).

        Args:
            conn: Active psycopg2 database connection.
            query_text: Rewritten query string for BM25.
            query_embedding: Dense vector embedding of the rewritten query.
            top_k: Number of candidates to retrieve from each search arm.

        Returns:
            List of chunk dicts sorted by descending RRF score.
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
            (0.75 * COALESCE(1.0 / (20 + v.vector_rank), 0.0)) + 
            (0.25 * COALESCE(1.0 / (20 + k.keyword_rank), 0.0)) AS rrf_score
        FROM chunks c
        LEFT JOIN vector_search v ON c.chunk_id = v.chunk_id
        LEFT JOIN keyword_search k ON c.chunk_id = k.chunk_id
        JOIN documents d ON c.document_id = d.id
        WHERE v.chunk_id IS NOT NULL OR k.chunk_id IS NOT NULL
        ORDER BY rrf_score DESC
        LIMIT %s;
        """

        with conn.cursor() as cur:
            # Register pgvector type adapter for this connection
            from pgvector.psycopg2 import register_vector
            register_vector(conn)

            cur.execute(sql, (
                query_embedding, query_embedding, top_k,    # vector arm
                query_text, query_text, query_text, top_k,  # keyword arm
                top_k,                                       # final limit
            ))
            rows = cur.fetchall()

        results = [
            {
                "chunk_id":     row[0],
                "content":      row[1],
                "heading_path": row[2],
                "breadcrumb":   row[3],
                "rrf_score":    float(row[4]),
            }
            for row in rows
        ]

        print(f"[RAGBase] Hybrid search retrieved {len(results)} chunks.")
        return results

    # ------------------------------------------------------------------
    # Step 3 — Cross-Encoder Reranking
    # ------------------------------------------------------------------

    def rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = RERANK_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks using the Cross-Encoder model and return top_k.

        Args:
            query: The (rewritten) query string.
            results: Candidate chunks from hybrid_search.
            top_k: Number of chunks to keep after reranking.

        Returns:
            Top-K chunks sorted by descending cross-encoder score.
        """
        if not results:
            return []

        if not getattr(self, 'use_reranker', True):
            print(f"[RAGBase] Skipping reranking (Fast Mode). Kept top {top_k} chunks.")
            return results[:top_k]

        documents = [res["content"] for res in results]
        print(f"[RAGBase] Reranking {len(documents)} chunks...")

        scores = self._cross_encoder.predict([(query, doc) for doc in documents])

        for i, score in enumerate(scores):
            results[i]["rerank_score"] = float(score)

        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        final = results[:top_k]
        print(f"[RAGBase] Kept top {len(final)} chunks after reranking.")
        return final

    # ------------------------------------------------------------------
    # Step 4 — LLM Answer Generation
    # ------------------------------------------------------------------

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Generate a grounded answer strictly from the retrieved context chunks.

        Args:
            query: Original user query (used for the final prompt).
            context_chunks: Reranked chunks providing factual context.

        Returns:
            The LLM-generated answer string with inline citations.
        """
        system_prompt = (
            "You are an expert Co-founder, HR, and Operations Advisor for a startup. "
            "Answer the user's query based ONLY on the provided context below. "
            "If the answer cannot be found in the context, say 'I cannot find the answer in the handbook.' "
            "Provide a highly structured, practical answer. Use bullet points and frameworks where applicable. "
            "When you use information from a source, add a citation at the end of the sentence or paragraph, "
            "like this: [Breadcrumb -> Heading Path]."
        )

        context_text = ""
        for idx, chunk in enumerate(context_chunks):
            breadcrumb   = chunk.get("breadcrumb", "")
            heading_path = chunk.get("heading_path", "")
            content      = chunk.get("content", "")
            context_text += (
                f"\n\n--- Source {idx + 1} ---\n"
                f"Breadcrumb: {breadcrumb} > {heading_path}\n"
                f"Content:\n{content}"
            )

        prompt = f"Context:\n{context_text}\n\nUser Query: {query}"

        print(f"[RAGBase] Generating answer using {len(context_chunks)} context chunks...")
        response = self._llm_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Orchestrator — Full RAG Pipeline
    # ------------------------------------------------------------------

    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Execute the complete RAG pipeline end-to-end.

        Steps: Rewrite → Embed → Hybrid Search → Rerank → Generate

        Args:
            user_query: The raw query string from the user.

        Returns:
            Dict with keys: user_query, rewritten_query, retrieved_chunks,
            answer, latency_seconds.
        """
        print(f"\n{'=' * 55}")
        print(f"[RAGBase] User Query: {user_query}")
        print(f"{'=' * 55}\n")

        t_start = time.perf_counter()

        # 1. Query rewriting
        rewritten_query = self.rewrite_query(user_query)

        # 2. Embedding
        query_embedding = embed_query(rewritten_query)

        # 3. Hybrid search + reranking
        conn = get_connection()
        try:
            candidates = self.hybrid_search(conn, rewritten_query, query_embedding)
            top_chunks = self.rerank_results(rewritten_query, candidates)
        finally:
            conn.close()

        # 4. Answer generation
        answer = self.generate_answer(user_query, top_chunks)

        latency = round(time.perf_counter() - t_start, 3)
        print(f"[RAGBase] Pipeline completed in {latency}s.")

        return {
            "user_query":       user_query,
            "rewritten_query":  rewritten_query,
            "retrieved_chunks": top_chunks,
            "answer":           answer,
            "latency_seconds":  latency,
        }
