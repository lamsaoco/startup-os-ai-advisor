# Capstone Project: Startup OS AI Advisor

## 1. Problem Statement

### Target Audience
* **First-time Founders & C-Levels:** Managers at scale-up startups facing critical organizational decisions.
* **HR / People Operations Managers:** Professionals responsible for culture, compensation, and performance frameworks.
* **Team Leads:** Middle managers learning how to lead teams, resolve conflicts, or manage underperformance.

### The Pain Points
In the chaotic environment of a growing startup, leaders constantly face high-stakes "first-time" challenges (e.g., distributing equity, firing a toxic high-performer, setting up performance reviews). 
1. **Time & Resource Constraints:** Founders do not have the time to read a 500-page management book or click through dozens of nested Notion wiki pages to find a specific framework.
2. **Generic AI Limitations:** Standard LLMs provide superficial, generic advice lacking proven, battle-tested management frameworks.
3. **High Consulting Costs:** Hiring HR or Operations consultants to set up basic company frameworks is prohibitively expensive for early-stage startups.

### The Solution: Startup OS AI Advisor
This project builds an **AI Operations & HR Advisor**. By ingesting the comprehensive, battle-tested knowledge from *The Company Building Handbook* (a complex, hierarchically structured Notion database), the system acts as a virtual Co-founder. Users can chat with the agent to get step-by-step guidance, exact frameworks, and practical templates instantly, with responses grounded strictly in the source material.

---

## 2. Core Use Cases (For Demo & Evaluation)

* **Use Case 1 (Crisis Management):** 
  * *Query:* "A top-performing sales rep is generating the most revenue but has a toxic attitude and violates company culture. What should I do? Provide a framework to handle this."
* **Use Case 2 (Process Setup):** 
  * *Query:* "We just hit 20 employees and need to set up our first Performance Review process. Where do we start and what are the exact steps?"
* **Use Case 3 (Organizational Structure & Comp):** 
  * *Query:* "Explain the difference between offering ESOP (Equity) versus Profit Sharing for middle managers. Which is better for retention?"

---

## 3. Technology Stack (AI Engineer Standard)

* **Environment & Package Management:** `uv` (Python 3.12+)
* **Data Ingestion:** `notion-client` (Recursive hierarchical crawling)
* **Orchestration:** Apache Airflow (DAG-based pipeline, runs in Docker)
* **Vector & Relational Database:** PostgreSQL with `pgvector` extension
* **Embedding Model:** Local ONNX Model (`BAAI/bge-large-en-v1.5`, dim 1024, MTEB ~54.3) via `fastembed`
* **Retrieval Framework:** Native Python
* **Search Strategy:** Hybrid Search (BM25 Full-text + Vector Embeddings) + Reciprocal Rank Fusion (RRF)
* **Re-ranking:** Cross-Encoder (Hugging Face)
* **LLM Generation:** Google Gemini `gemini-2.0-flash-lite` (via OpenAI SDK)
* **User Interface:** Streamlit
* **Monitoring & Observability:** Grafana (Dashboards connected to PostgreSQL)
* **Deployment:** Docker Compose, AWS Cloud (AWS ECS / EC2)

---

## 4. Master Execution Plan (Step-by-Step Tasks)

### Phase 1: Project & Environment Setup
- [x] Initialize project directory and Git repository.
- [x] Setup Python environment using `uv` (`uv venv`, `uv add ...`).
- [x] Add `.gitignore` and `.env.example`.
- [x] Create `docker-compose.yml` to spin up PostgreSQL (`pgvector`), Grafana, pgAdmin, and Airflow.
- [x] Initialize database schema (Tables: `documents`, `chunks`, `app_monitoring_logs`) — handled in `loader.py::init_schema()`.

### Phase 2: Hierarchical Data Ingestion
- [x] Duplicate "The Company Building Handbook" to personal Notion workspace.
- [x] Create Notion Integration and obtain `NOTION_API_KEY`.
- [x] Write `ingestion/notion_crawler.py` — recursive crawler with pagination & rate-limit retry.
- [x] Implement **Recursive Crawling** — captures parent-child page relationships and breadcrumb.
- [x] Write `ingestion/text_extractor.py` — converts Notion blocks to structured plain text.
- [x] Write `ingestion/chunker.py` — heading-aware chunking with token-based size control.
- [x] Write `ingestion/embedder.py` — batch embedding via local ONNX model (`fastembed`).
- [x] Write `ingestion/loader.py` — upsert chunks + embeddings into PostgreSQL.
- [x] Write Airflow DAGs: `dags/01_notion_extraction_dag.py` & `dags/02_notion_transform_load_dag.py`.
- [x] Trigger the Airflow DAG and verify chunks loaded correctly into PostgreSQL.

### Phase 3: Advanced Retrieval & Generation Pipeline
- [x] Implement **Query Rewriting** using `gemini-3.1-flash-lite` to expand synonyms.
- [x] Implement **Hybrid Search**: pgvector cosine similarity + `to_tsvector` BM25.
- [x] Implement **Reciprocal Rank Fusion (RRF)** to merge vector and keyword results.
- [x] Implement **Document Re-ranking**: Cross-Encoder (Hugging Face) for Top-K reranking.
- [x] Build generation prompt and final response via `gemini-3.1-flash-lite` (OpenAI SDK).

### Phase 4: System Evaluation (Retrieval & LLM)
- [x] Create a Ground Truth dataset — Synthetic QA Generation (100 chunks × 3 Q = 300 pairs).
- [x] Evaluate Retrieval: **Hit Rate@K** and **MRR** — Vector vs. Hybrid vs. Hybrid+Reranker.
- [x] Evaluate LLM: Gemini-as-a-judge scoring Faithfulness=5.0/5.0 and Answer Relevance=5.0/5.0 (50 samples).
- [x] Document evaluation results in `README.md`.

### Phase 4.5: Retrieval Optimization (Root-cause fixes from evaluation)
- [x] Identify root causes of low Hit Rate (21.3%) — chunking, model, missing context.
- [x] Switch embedding model: `mpnet-768d` → `BAAI/bge-large-en-v1.5` (1024d, MTEB ~54.3).
- [x] Add `embed_text` field to `Chunk`: contextual prefix `[Document: X | Path: Y]` + content used for embedding only; raw `content` kept separate for display.
- [x] Add sliding window overlap (`CHUNK_OVERLAP_TOKENS=64`) between paragraph sub-chunks.
- [x] Increase `CHUNK_MAX_TOKENS`: 450 → 512.
- [x] Fix numbered list rendering (`1. 1. 1.` → `1. 2. 3.`).
- [x] Increase `RETRIEVAL_TOP_K`: 20 → 40; `RERANK_TOP_K`: 5 → 10.
- [x] Create `ingestion/migrate_schema.py` to DROP+recreate chunks table (dim change).
- [x] Document known issues & optimization roadmap in `README.md`.
- `[x]` Run migration + re-ingest + re-evaluate to measure improvement.

### Phase 5: Streamlit Interface & Feedback Logging
- `[x]` Build a Streamlit chat interface.
- `[x]` Display citations/sources (Breadcrumbs) below each LLM response.
- `[x]` Add interactive Thumbs Up / Thumbs Down feedback buttons.
- `[x]` Log every interaction (Query, Response, Latency, Rating, Retrieved Chunks) to `app_monitoring_logs`.

### Phase 6: Monitoring Dashboard
- [x] Connect local Grafana to the PostgreSQL database (auto-provisioned via `docker/grafana/provisioning/datasources/postgres.yml`).
- [x] Build Dashboard Chart 1: Total Queries Over Time.
- [x] Build Dashboard Chart 2: Average System Latency.
- [x] Build Dashboard Chart 3: User Satisfaction Score (Thumbs up ratio).
- [x] Build Dashboard Chart 4: Negative Feedback Logs (Table view for debugging).
- [x] Export Grafana dashboard JSON to repository (`docker/grafana/dashboards/monitoring.json`).

### Phase 7: Containerization & Cloud Deployment
- `[x]` Write a `Dockerfile` for the Streamlit application.
- `[x]` Update `docker-compose.yml` to include the Streamlit app container.
- `[x]` Provision AWS infrastructure (EC2 `t3.micro` recommended for cost).
- [ ] Deploy the complete system to AWS and ensure public access.

### Phase 8: Final Documentation
- [ ] Write a comprehensive `README.md` addressing all Capstone evaluation criteria.
- [ ] Add system architecture diagrams.
- [ ] Include Evaluation Results (Hit Rate, MRR, Faithfulness scores).
- [ ] Provide clear instructions on how to run locally via Docker.
- [ ] Record a short 2-3 minute demo video (UI, search quality, Grafana dashboard).