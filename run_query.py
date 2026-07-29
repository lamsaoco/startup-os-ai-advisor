import argparse
from retrieval.pipeline import run_rag_pipeline

def main():
    parser = argparse.ArgumentParser(description="Query the Startup OS AI Advisor RAG Pipeline")
    parser.add_argument("query", type=str, help="The query string to search for")
    args = parser.parse_args()

    result = run_rag_pipeline(args.query)

    print(f"\n=======================================================")
    print(f"Final Answer:")
    print(f"=======================================================\n")
    print(result["answer"])
    
    print(f"\n=======================================================")
    print(f"Sources Used (Top {len(result['retrieved_chunks'])}):")
    print(f"=======================================================\n")
    for i, chunk in enumerate(result['retrieved_chunks']):
        print(f"[{i+1}] {chunk['breadcrumb']} > {chunk['heading_path']}")
        print(f"    RRF Score: {chunk.get('rrf_score', 0):.4f} | Rerank Score: {chunk.get('rerank_score', 0):.4f}")

if __name__ == "__main__":
    main()
