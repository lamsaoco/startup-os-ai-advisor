"""
RAG Pipeline — Orchestrator combining rewriting, embedding, hybrid search, reranking, and generation.
"""
from typing import Dict, Any

from ingestion.loader import get_connection
from ingestion.embedder import embed_query
from retrieval.llm_client import rewrite_query, generate_answer
from retrieval.search import hybrid_search, rerank_results

def run_rag_pipeline(user_query: str) -> Dict[str, Any]:
    """
    Executes the full Retrieval-Augmented Generation pipeline.
    """
    print(f"\n=======================================================")
    print(f"User Query: {user_query}")
    print(f"=======================================================\n")
    
    # 1. Rewrite Query
    rewritten_query = rewrite_query(user_query)
    
    # 2. Embed Query
    # Note: embed_query expects a single string and returns list[float]
    query_embedding = embed_query(rewritten_query)
    
    # 3. Retrieve & Rerank
    conn = get_connection()
    try:
        results = hybrid_search(conn, rewritten_query, query_embedding)
        top_results = rerank_results(rewritten_query, results)
    finally:
        conn.close()
        
    # 4. Generate Answer
    answer = generate_answer(user_query, top_results)
    
    return {
        "user_query": user_query,
        "rewritten_query": rewritten_query,
        "retrieved_chunks": top_results,
        "answer": answer
    }
