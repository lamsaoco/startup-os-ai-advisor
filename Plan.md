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
* **Data Ingestion:** `dlt` (Data Load Tool) + Notion API (Recursive hierarchical crawling)
* **Vector & Relational Database:** PostgreSQL with `pgvector` extension
* **Embedding Model:** Google Gemini `text-embedding-004`
* **Retrieval Framework:** Native Python / LangChain
* **Search Strategy:** Hybrid Search (BM25 Full-text + Vector Embeddings) + Reciprocal Rank Fusion (RRF)
* **Re-ranking:** Cohere Rerank / Cross-Encoder
* **LLM Generation:** Google Gemini (`gemini-1.5-pro` for deep reasoning, `gemini-1.5-flash` for query rewriting)
* **User Interface:** Streamlit
* **Monitoring & Observability:** Grafana (Dashboards connected to PostgreSQL)
* **Deployment:** Docker Compose, AWS Cloud (AWS ECS / EC2)

---

## 4. Master Execution Plan (Step-by-Step Tasks)

### Phase 1: Project & Environment Setup
- [ ] Initialize project directory and Git repository.
- [ ] Setup Python environment using `uv` (e.g., `uv venv`, `uv pip install ...`).
- [ ] Create `docker-compose.yml` to spin up PostgreSQL (`pgvector`) and Grafana locally.
- [ ] Initialize database schema (Tables for: `documents`, `chunks`, `app_monitoring_logs`).

### Phase 2: Hierarchical Data Ingestion
- [ ] Duplicate "The Company Building Handbook" to personal Notion workspace.
- [ ] Create Notion Integration and obtain `NOTION_API_KEY`.
- [ ] Write a Python script using `dlt` or standard requests to fetch pages from Notion via API.
- [ ] Implement **Recursive Crawling**: Ensure the script captures parent-child page relationships.
- [ ] Implement **Hierarchical Chunking**: Split text while preserving metadata (`page_title`, `parent_page`, `breadcrumb`).
- [ ] Generate vector embeddings using Gemini `text-embedding-004` and load chunks + metadata into PostgreSQL.

### Phase 3: Advanced Retrieval & Generation Pipeline
- [ ] Implement **Query Rewriting**: Write a prompt using `gemini-1.5-flash` to expand the user's query with management synonyms.
- [ ] Implement **Hybrid Search**: Write SQL queries using `pgvector` for Cosine Similarity and `to_tsvector` for BM25.
- [ ] Implement **Reciprocal Rank Fusion (RRF)** to combine Vector and Keyword search results.
- [ ] Implement **Document Re-ranking**: Pass the Top-K results through a Re-ranker model to get the final Top-3 chunks.
- [ ] Build the Generation Prompt: Inject the Top-3 chunks and construct the final response using `gemini-1.5-pro` via the official `google-genai` SDK.

### Phase 4: System Evaluation (Retrieval & LLM)
- [ ] Create a Ground Truth dataset (15-20 Q&A pairs with corresponding correct chunk IDs).
- [ ] Evaluate Retrieval: Calculate **Hit Rate@K** and **MRR** comparing Vector Search vs. Hybrid Search vs. Hybrid + Reranker.
- [ ] Evaluate LLM: Use `ragas` or LLM-as-a-judge (using Gemini) to score answers on Faithfulness and Answer Relevance.
- [ ] Document evaluation results.

### Phase 5: Streamlit Interface & Feedback Logging
- [ ] Build a Streamlit chat interface.
- [ ] Display citations/sources (Breadcrumbs) below each LLM response.
- [ ] Add interactive Thumbs Up / Thumbs Down feedback buttons.
- [ ] Write logic to log every interaction (User Query, Response, Latency, Rating) to the PostgreSQL `app_monitoring_logs` table.

### Phase 6: Monitoring Dashboard
- [ ] Connect local Grafana to the PostgreSQL database.
- [ ] Build Dashboard Chart 1: Total Queries Over Time.
- [ ] Build Dashboard Chart 2: Average System Latency.
- [ ] Build Dashboard Chart 3: User Satisfaction Score (Thumbs up ratio).
- [ ] Build Dashboard Chart 4: Negative Feedback Logs (Table view for debugging).
- [ ] Export Grafana dashboard JSON to include in the repository.

### Phase 7: Containerization & Cloud Deployment
- [ ] Write a `Dockerfile` for the Streamlit application.
- [ ] Update `docker-compose.yml` to include the Streamlit app container alongside DB and Grafana.
- [ ] Provision AWS infrastructure (AWS ECS or an EC2 instance).
- [ ] Deploy the complete system to AWS and ensure it is accessible via public IP/Domain.

### Phase 8: Final Documentation
- [ ] Write a comprehensive `README.md` addressing all Capstone evaluation criteria.
- [ ] Add system architecture diagrams.
- [ ] Provide clear, step-by-step instructions on how to run the project locally via Docker.
- [ ] Record a short 2-3 minute demo video showing the UI, search quality, and Grafana dashboard.