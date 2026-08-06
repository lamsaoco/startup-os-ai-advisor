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

A random sample of 30 Q&A pairs was evaluated using `gemini-3.1-flash-lite` as an impartial judge.

| Metric | Score |
|---|---|
| Avg Faithfulness | 5.00 / 5.0 |
| Avg Answer Relevance | 5.00 / 5.0 |
| Samples evaluated | 30 |

**Conclusion**: When relevant chunks are retrieved, the LLM generates accurate, hallucination-free answers. The bottleneck is **retrieval quality**, not generation quality.

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

