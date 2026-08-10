# Evaluation Report

**Generated:** 2026-08-10 02:51:42  
**Ground Truth Size:** 300 Q&A pairs

## Retrieval Evaluation

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.583 | 0.723 | 0.793 | 0.860 | 0.583 | 0.647 | 0.663 | 0.672 |
| hybrid | 0.587 | 0.727 | 0.793 | 0.860 | 0.587 | 0.651 | 0.666 | 0.675 |
| hybrid_reranker | 0.680 | 0.803 | 0.843 | 0.843 | 0.680 | 0.739 | 0.748 | 0.748 |

## LLM Quality Evaluation

| Metric | Score |
|---|---|
| Avg Faithfulness    | 0.00 / 5.0 |
| Avg Answer Relevance | 0.00 / 5.0 |
| Samples evaluated   | 0 |
