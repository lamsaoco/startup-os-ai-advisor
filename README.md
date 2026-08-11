# Startup OS AI Advisor

An AI-powered advisor that answers questions about company building, HR practices, and startup operations by querying a private Notion knowledge base via Retrieval-Augmented Generation (RAG).

---

## Evaluation Results (Phase 4 — Baseline)

We generated a synthetic ground truth dataset of **300 Q&A pairs** (3 questions each for 100 random document chunks) using `gemini-3.1-flash-lite`. We then evaluated our RAG pipeline across three retrieval strategies.

### 1. Retrieval Performance (Baseline — mpnet 768d, no overlap, no breadcrumb embedding)

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.127 | 0.170 | 0.180 | 0.190 | 0.127 | 0.147 | 0.149 | 0.151 |
| hybrid | 0.137 | 0.190 | 0.200 | 0.210 | 0.137 | 0.161 | 0.163 | 0.165 |
| hybrid_reranker | 0.197 | 0.210 | 0.213 | 0.213 | 0.197 | 0.203 | 0.204 | 0.204 |

**Conclusion**: The `hybrid_reranker` strategy (pgvector + BM25 + Cross-Encoder) outperforms other methods. However, **Hit@5 of 21.3% is below production threshold** — only 64 of 300 queries found their source chunk.

### 2. LLM Quality Evaluation (Gemini-as-a-Judge)

A random sample of **50 Q&A pairs** was evaluated using `gemini-2.0-flash-lite` as an impartial judge on two axes: **Faithfulness** (is the answer grounded in the retrieved context?) and **Answer Relevance** (does the answer address the user's question?).

| Metric | Baseline (30 samples) | Phase 4.6 (50 samples) |
|---|---|---|
| Avg Faithfulness | 5.00 / 5.0 | **5.00 / 5.0** |
| Avg Answer Relevance | 5.00 / 5.0 | **5.00 / 5.0** |
| Samples evaluated | 30 | 50 |

**Conclusion**: The LLM generation layer is **perfect** — when the retrieval pipeline surfaces the correct context, Gemini consistently produces faithful, relevant, and hallucination-free answers. The **retrieval quality (Hit Rate)** remains the only bottleneck to address.

---

## Project Story: The Evolution of our RAG Pipeline (Phase 4 → Phase 5)

After establishing our Phase 4 baseline, we ran a synthetic evaluation and found that our **Hit@5 was only 21.3%** — a critical bottleneck. The LLM was answering perfectly when given the right context, but the retrieval engine was struggling to find it.

This section documents the journey of analyzing these failures and the architectural changes we made in Phase 5 to solve them.

### Issue 1 — Embedding Model Was General-Purpose (Not Domain-Optimized)

**Model**: `paraphrase-multilingual-mpnet-base-v2` (dim 768, MTEB ~45)

This model was selected initially for its multilingual support and small footprint. However:
- The knowledge base is entirely in **English** → multilingual support wastes capacity
- MTEB Retrieval score of ~45 is significantly below state-of-the-art English models (~54+)
- General-purpose embeddings fail to distinguish between semantically similar HR/operations concepts (e.g., "reimbursement policy" vs. "expense procedure")

**Fix**: Switched to `BAAI/bge-large-en-v1.5` (dim 1024, MTEB ~54.3), the highest-quality English model natively supported by fastembed ONNX.

---

### Issue 2 — Chunks Lost Document Context After Splitting

**Problem**: After splitting a Notion page into chunks, each chunk only contained raw text. The embedding model had no idea which document or section the chunk came from.

**Example**: A chunk containing _"Employees must submit an expense receipt to finance@company.com"_ looks identical whether it's from Blendle's handbook or Sparksuite's — but they may have different policies.

**Fix**: Each chunk now has an `embed_text` field (used for embedding only, not shown to users):

```
[Document: Blendle's Employee Handbook | Path: Travel > Reimbursements]
Employees must submit an expense receipt to finance@blendle.com.
```

The raw `content` field is unchanged and used for display/answer generation.

---

### Issue 3 — No Sliding Window Overlap

**Problem**: Chunk boundaries hard-cut paragraph sequences. A question about a concept that spans the end of one chunk and the beginning of the next would never match either chunk well.

**Fix**: When splitting oversized sections by paragraph, the last `CHUNK_OVERLAP_TOKENS = 64` tokens of the previous chunk are prepended to the next one. This ensures boundary sentences appear in both chunks.

---

### Issue 4 — Numbered Lists Rendered as `1. 1. 1.`

**Problem**: All `numbered_list_item` blocks from Notion were rendered as `1.` regardless of position. This broke list semantics and degraded embedding quality for procedural content.

**Fix**: A counter now increments within each consecutive numbered list sequence and resets when a non-list block is encountered.

---

### Issue 5 — Retrieval Pool Was Too Small

**Problem**: `RETRIEVAL_TOP_K=20` and `RERANK_TOP_K=5` left very little room for the cross-encoder to recover relevant chunks that ranked poorly in the initial vector/BM25 step.

**Fix**: Increased to `RETRIEVAL_TOP_K=40` and `RERANK_TOP_K=10` to widen the initial funnel.

---

### Issue 6 — The "Phantom" 17% Hit Rate (Database Misconfiguration)

**Problem**: Despite upgrading to `bge-large`, adding breadcrumbs, and increasing `top_k`, our Hit@5 and Hit@10 metrics flatlined at exactly 17.0%. Diagnostic tests revealed two critical bugs:
1. **IVFFlat Index Starvation**: The pgvector `ivfflat` index was created with `lists=50`, but the search was executed with the default `ivfflat.probes=1`. This meant Postgres only searched 1/50th of the database (about 24 chunks) and skipped the other 1,180 chunks entirely! For a dataset this small (~1200 chunks), using an approximate index is actually counter-productive.
2. **Hardcoded Evaluation Limit**: `run_evaluation.py` was hardcoded to `top_k=20`, silently overriding our new `RETRIEVAL_TOP_K=40` configuration during tests.

**Fix**: 
- Dropped the IVFFlat index from the schema entirely. For ~1200 chunks, Exact Nearest Neighbor Search (SeqScan) executes in <1ms and guarantees 100% recall.
- Replaced the hardcoded `top_k` in the evaluation script with the dynamic config values.

---

## Evaluation Results (Phase 4.5 — Post-Optimization)

After implementing the Phase 4.5 optimizations (BGE-Large model, breadcrumb embedding, overlap, Exact Search, and increased top_k), the retrieval performance improved drastically.

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.583 | 0.723 | 0.793 | 0.860 | 0.583 | 0.647 | 0.663 | 0.672 |
| hybrid | 0.583 | 0.727 | 0.793 | 0.860 | 0.583 | 0.649 | 0.665 | 0.673 |
| hybrid_reranker | 0.680 | 0.817 | 0.867 | 0.907 | 0.680 | 0.745 | 0.756 | 0.761 |

**Conclusion**: The system now retrieves the correct chunk in the top 5 results **86.7% of the time** (up from 21.3%). The top 10 recall is **90.7%**. This exceeds the production-ready threshold and confirms our architecture choices.

---

## Phase 4.6 — Advanced Retrieval Tuning (Hitting 90%+)

Even with an 86.7% Hit Rate, we implemented two additional targeted tuning methods to push the hybrid search to its absolute limit:

### Tuning 1: BM25 Breadcrumb Indexing (Schema Change)
**Problem**: The keyword search (BM25) originally indexed only the raw text `content`. If a user asked a specific policy question (e.g., "What is the ESOP policy?"), and the term "ESOP" only appeared in the document title or heading, BM25 would fail to find it.
**Fix**: Altered the database schema so the `content_tsv` column is generated using `embed_text` (which includes the Breadcrumb and Heading Path). Now, BM25 correctly matches category names and hierarchical terms perfectly.

### Tuning 2: Weighted Reciprocal Rank Fusion
**Problem**: The RRF algorithm was splitting the score 50/50 between Vector Search and BM25: `1.0 / (60 + rank)`. Because our local BGE-Large vector model is extraordinarily accurate for semantic queries, assigning 50% weight to BM25 was diluting the vector results with keyword noise.
**Fix**: Updated `rag_base.py` to use a weighted RRF formula prioritizing semantic search, while also tightening the constant ($k=20$) to heavily favor the absolute top results:
`RRF = (0.75 * 1.0 / (20 + vector_rank)) + (0.25 * 1.0 / (20 + bm25_rank))`

### Final Evaluation Results (Phase 4.6 - Optimized for Memory/Speed)

After implementing the above optimizations and reducing `RETRIEVAL_TOP_K=15` and `RERANK_TOP_K=5` to prevent Out-Of-Memory (OOM) crashes on the server, the final metrics over the 300 Q&A Ground Truth dataset are:

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.583 | 0.723 | 0.793 | 0.860 | 0.583 | 0.647 | 0.663 | 0.672 |
| hybrid | 0.587 | 0.727 | 0.793 | 0.860 | 0.587 | 0.651 | 0.666 | 0.675 |
| hybrid_reranker | 0.680 | 0.803 | 0.843 | 0.843 | 0.680 | 0.739 | 0.748 | 0.748 |

**Conclusion:** 
While the Hit Rate slightly dropped from 86.7% to 84.3% due to reducing the Reranker window (Top 40 -> Top 15), this trade-off was necessary to solve catastrophic OOM crashes and reduce latency from 37s -> 4s. The Fast Mode (`hybrid` without Reranker) still achieves nearly 80% Hit Rate and is used by default in the UI for optimal user experience.

---

## Optimization Roadmap

| Phase | Change | Status |
|---|---|---|
| **P4 Baseline** | mpnet 768d, heading-split, hybrid+reranker | ✅ Done |
| **P5 Chunking v2** | Overlap 64 tokens, breadcrumb in embed_text, fix numbered list | ✅ Done |
| **P5 Model** | Switch to `BAAI/bge-large-en-v1.5` (1024d, MTEB ~54.3) | ✅ Done |
| **P5 Retrieval** | RETRIEVAL_TOP_K 20→40, RERANK_TOP_K 5→10 | ✅ Done |
| **P6 (Future)** | Multi-query retrieval (3 sub-queries per question) | ⬜ Planned |
| **P6 (Future)** | Fine-tune embedding on domain Q&A pairs | ⬜ Planned |
| **P6 (Future)** | HyDE (Hypothetical Document Embeddings) | ⬜ Planned |

---

## Architecture

```
Notion Workspace
      ↓  [notion_crawler.py]
  PageData objects
      ↓  [text_extractor.py]
  Markdown text (headings, bullets, tables preserved)
      ↓  [chunker.py]
  Chunks (content + embed_text with breadcrumb prefix + overlap)
      ↓  [embedder.py — BAAI/bge-large-en-v1.5 ONNX local]
  1024-dim embeddings
      ↓  [loader.py]
  PostgreSQL + pgvector

Query Time:
  User Query
      ↓  Query Rewriting (Gemini)
      ↓  Hybrid Search (pgvector cosine + BM25 + RRF)
      ↓  Cross-Encoder Reranking (BAAI/bge-reranker-base)
      ↓  Answer Generation (Gemini)
  Answer with citations
```

## Re-ingestion After Schema Changes

The `airflow` container is already running inside the Docker network and has all project code mounted. Use it to run any CLI script without building anything extra:

```bash
# Drop & recreate the chunks table (one-time, after model/schema change)
docker compose exec airflow uv run python -m scripts.migrate_schema

# Trigger Airflow DAGs to re-ingest all Notion documents
# Open http://localhost:8080 → trigger DAGs manually
```

