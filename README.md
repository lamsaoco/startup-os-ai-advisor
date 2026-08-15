# Capstone Project: Startup OS AI Advisor 🚀

An AI-powered virtual Co-founder and HR Operations Advisor that answers questions about company building, HR practices, and startup operations by querying a private Notion knowledge base via a highly optimized Retrieval-Augmented Generation (RAG) pipeline.

---

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

---

## 2. The Solution

**Startup OS AI Advisor** solves this by ingesting the comprehensive, battle-tested knowledge from *The Company Building Handbook* (a complex, hierarchically structured Notion database). 

Users can chat with the agent to get step-by-step guidance, exact frameworks, and practical templates instantly, with responses grounded strictly in the source material.

### Core Use Cases (Demo)

* **Use Case 1 (Crisis Management):** 
  * *Query:* "A top-performing sales rep is generating the most revenue but has a toxic attitude and violates company culture. What should I do?"
* **Use Case 2 (Process Setup):** 
  * *Query:* "We just hit 20 employees and need to set up our first Performance Review process. Where do we start and what are the exact steps?"
* **Use Case 3 (Organizational Structure & Comp):** 
  * *Query:* "Explain the difference between offering ESOP (Equity) versus Profit Sharing for middle managers."

> **[INSERT VIDEO: Demo_Video.mp4]**
> *(Please insert a 2-3 minute video here demonstrating the UI, search quality, and Grafana dashboard)*

> **[INSERT IMAGE: Chat_Interface.png]**
> *(Please insert a screenshot of the Streamlit Chat Interface showing a query and response)*

---

## 3. Technology Stack (AI Engineer Standard)

* **Environment & Package Management:** `uv` (Python 3.12+)
* **Data Ingestion:** `notion-client` (Recursive hierarchical crawling)
* **Orchestration:** Apache Airflow (DAG-based pipeline, runs in Docker)
* **Vector & Relational Database:** PostgreSQL with `pgvector` extension
* **Embedding Model:** Local ONNX Model (`BAAI/bge-large-en-v1.5`, dim 1024) via `fastembed`
* **Retrieval Framework:** Native Python (Hybrid Search: BM25 + Vector + RRF)
* **Re-ranking:** Cross-Encoder (`BAAI/bge-reranker-base`) via Hugging Face/PyTorch
* **LLM Generation:** Google Gemini `gemini-2.0-flash-lite` (via OpenAI SDK API)
* **User Interface:** Streamlit (Custom styled UI with loading states)
* **Monitoring & Observability:** Grafana (Dashboards connected to PostgreSQL)
* **Deployment:** Docker Compose, AWS Cloud (AWS EC2)

---

## 4. System Architecture

```mermaid
graph TD
    subgraph Data Ingestion Pipeline (Airflow DAGs)
        A[Notion Workspace] -->|notion-client API| B(notion_crawler.py)
        B --> C{PageData Objects}
        C -->|Markdown Text| D(text_extractor.py)
        D -->|Heading-aware Splitting| E(chunker.py)
        E -->|Chunks + Breadcrumb Overlap| F(embedder.py)
        F -->|BAAI/bge-large-en-v1.5| G[(PostgreSQL + pgvector)]
    end

    subgraph User Interaction (Streamlit)
        U((User)) -->|Query| UI[Streamlit App]
    end

    subgraph RAG Retrieval Pipeline
        UI -->|Query| QR[Query Rewriter (Gemini)]
        QR -->|Synonyms & Expansions| HS{Hybrid Search}
        HS -->|Cosine Similarity| G
        HS -->|BM25 Full Text Search| G
        G -->|Top 40 Vector + Top 40 Keyword| RRF[Reciprocal Rank Fusion]
        RRF -->|Top 15 Combined| CE[Cross-Encoder Reranker]
        CE -->|Top 5 Context Chunks| LLM[LLM Generation (Gemini-2.0-Flash-lite)]
    end

    LLM -->|Answer + Citations| UI
    UI -->|Log Query, Latency, Feedback| L[(App Monitoring DB)]
    
    subgraph Observability
        L --> GR[Grafana Dashboard]
    end
```

> **[INSERT IMAGE: Architecture_Diagram.png]**
> *(Please insert a high-resolution version of the architecture diagram if preferred over the Mermaid chart above)*

---

## 5. Monitoring & Observability

Every query, LLM response, retrieval latency, and user feedback (Thumbs Up / Thumbs Down) is logged to the PostgreSQL database. Grafana is connected to visualize these metrics in real-time.

> **[INSERT IMAGE: Grafana_Dashboard.png]**
> *(Please insert a screenshot of the Grafana Dashboard showing Total Queries, Latency, and User Satisfaction Score)*

---

## 6. Evaluation Results & Pipeline Evolution (Phase 4 → Phase 5)

We generated a synthetic ground truth dataset of **300 Q&A pairs** (3 questions each for 100 random document chunks) using `gemini-3.1-flash-lite`. 

### Initial Baseline (Phase 4)
* **Model**: `paraphrase-multilingual-mpnet-base-v2` (dim 768)
* **Hit@5**: **21.3%**
* **Conclusion**: The LLM generation was perfect (5.0/5.0 Faithfulness) when context was found, but the retrieval engine was severely lacking.

### The Optimization Journey (Phase 4.5 & 4.6)
To push retrieval performance beyond the production threshold, we implemented:
1. **Domain-Optimized Model:** Switched to `BAAI/bge-large-en-v1.5` (1024d) for superior English semantic search.
2. **Contextual Breadcrumbs:** Each chunk now includes a hierarchical prefix (e.g., `[Document: Handbook | Path: Travel > Reimbursements]`) to maintain context for embedding and BM25 indexing.
3. **Sliding Window Overlap:** Added 64-token overlap to prevent information loss at paragraph boundaries.
4. **BM25 Schema Tuning:** BM25 now searches over the breadcrumbs and headings, not just raw content.
5. **Weighted RRF:** Modified the Reciprocal Rank Fusion formula to `(0.75 * Vector) + (0.25 * BM25)` to favor the highly accurate BGE-Large semantic embeddings while still catching keyword matches.

### Final Optimized Results (Phase 4.6)

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.583 | 0.723 | 0.793 | 0.860 | 0.583 | 0.647 | 0.663 | 0.672 |
| hybrid | 0.587 | 0.727 | 0.793 | 0.860 | 0.587 | 0.651 | 0.666 | 0.675 |
| **hybrid_reranker** | **0.680** | **0.803** | **0.843** | **0.843** | **0.680** | **0.739** | **0.748** | **0.748** |

**Conclusion**: The system now retrieves the correct chunk in the top 5 results **84.3% of the time** (up from 21.3%), heavily exceeding the production-ready threshold. To prevent Out-Of-Memory (OOM) crashes in constrained 8GB RAM environments, `RETRIEVAL_TOP_K` was intentionally bounded to 15, prioritizing extreme stability and low latency (~4s per query) over a marginal 2% recall gain.

---

## 7. Setup & Run Instructions

### 7.1. Running Locally via Docker Compose

1. **Clone the repository:**
   ```bash
   git clone <repo_url>
   cd startup-os-ai-advisor
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   # Notion API (For Data Ingestion)
   NOTION_API_KEY=secret_...
   NOTION_ROOT_PAGE_ID=...
   
   # LLM API (For Generation & Rewriting)
   GEMINI_API_KEY=AIzaSy...
   
   # Database Connections
   DATABASE_URL=postgresql://postgres:postgres@postgres:5432/startup_os
   AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://postgres:postgres@postgres:5432/startup_os
   ```

3. **Start the System:**
   ```bash
   docker compose up -d
   ```

4. **Access the Services:**
   - **Streamlit Chat UI:** `http://localhost:8501`
   - **Airflow UI:** `http://localhost:8080` (Trigger the DAGs here to ingest Notion data)
   - **Grafana Dashboard:** `http://localhost:3000` (Default login: `admin`/`admin`)
   - **pgAdmin:** `http://localhost:5050`

### 7.2. Cloud Deployment (AWS EC2)

1. Provision an **AWS EC2 Ubuntu Instance** (t3.medium or higher recommended for 8GB RAM to support the local Reranker).
2. Attach an **Elastic IP** and configure the **Security Group** to allow inbound traffic on:
   - `Port 80 / 443` (HTTP/HTTPS if using reverse proxy)
   - `Port 8501` (Streamlit)
   - `Port 3000` (Grafana)
3. SSH into the instance and install Docker and Git.
4. Clone the repository, add the `.env` file, and run `docker compose up -d`.
5. Access the application publicly via `http://<EC2_PUBLIC_IP>:8501`.

---
*Built as a Capstone Project by [Your Name]*
