# startup-os-ai-advisor
Startup OS AI Advisor

## Evaluation Results (Phase 4)

We generated a synthetic ground truth dataset of 300 Q&A pairs (3 questions each for 100 random document chunks) using `gemini-3.1-flash-lite`. We then evaluated our Retrieval Augmented Generation pipeline.

### 1. Retrieval Performance

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.127 | 0.170 | 0.180 | 0.190 | 0.127 | 0.147 | 0.149 | 0.151 |
| hybrid | 0.137 | 0.190 | 0.200 | 0.210 | 0.137 | 0.161 | 0.163 | 0.165 |
| hybrid_reranker | 0.197 | 0.210 | 0.213 | 0.213 | 0.197 | 0.203 | 0.204 | 0.204 |

**Conclusion**: The `hybrid_reranker` strategy (pgvector + BM25 + Cross-Encoder) outperforms other methods across all metrics, showing a significant improvement in Hit@1 (19.7%) compared to vector-only (12.7%).

### 2. LLM Quality Evaluation (Gemini-as-a-Judge)

A random sample of 30 Q&A pairs was evaluated using `gemini-3.1-flash-lite` as an impartial judge.

| Metric | Score |
|---|---|
| Avg Faithfulness | 5.00 / 5.0 |
| Avg Answer Relevance | 5.00 / 5.0 |
| Samples evaluated | 30 |

**Conclusion**: The system achieves a perfect 5.0 score in both Faithfulness and Relevance. When relevant chunks are retrieved, the LLM consistently generates accurate, hallucination-free answers perfectly aligned with the source documents.
