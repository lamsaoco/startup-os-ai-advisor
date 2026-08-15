import streamlit as st

st.set_page_config(layout="wide", page_title="System Architecture Diagram")

st.title("🏗️ Startup OS AI Advisor - System Architecture")
st.markdown("Run this script locally to generate and capture the architecture diagram for the README.")

st.graphviz_chart('''
digraph G {
    rankdir=TD;
    node [shape=box, style="rounded,filled", fillcolor="#1e293b", fontcolor="white", color="#475569", fontname="Arial"];
    edge [color="#94a3b8", fontname="Arial", fontsize=10];
    bgcolor="transparent";
    
    subgraph cluster_ingestion {
        label="Data Ingestion (Airflow)";
        fontcolor="#e2e8f0";
        color="#334155";
        style="rounded,dashed";
        
        Notion [label="Notion Workspace"];
        Crawler [label="notion_crawler.py"];
        Extractor [label="text_extractor.py"];
        Chunker [label="chunker.py"];
        Embedder [label="embedder.py\\n(BAAI/bge-large-en)"];
        DB [label="PostgreSQL + pgvector", shape=cylinder, fillcolor="#0f172a"];
        
        Notion -> Crawler -> Extractor -> Chunker -> Embedder -> DB;
    }
    
    subgraph cluster_rag {
        label="RAG Pipeline";
        fontcolor="#e2e8f0";
        color="#334155";
        style="rounded,dashed";
        
        QueryRewriter [label="Query Rewriter\\n(Gemini)"];
        HybridSearch [label="Hybrid Search\\n(Cosine + BM25)"];
        RRF [label="Reciprocal Rank Fusion"];
        CrossEncoder [label="Cross-Encoder Reranker"];
        LLM [label="LLM Generation\\n(Gemini)"];
        
        QueryRewriter -> HybridSearch -> RRF -> CrossEncoder -> LLM;
    }
    
    User [shape=ellipse, fillcolor="#3b82f6", label="User (Streamlit)"];
    Monitoring [shape=cylinder, fillcolor="#0f172a", label="Monitoring Logs"];
    Grafana [label="Grafana Dashboard", fillcolor="#f59e0b", fontcolor="black"];
    
    User -> QueryRewriter [label="Query"];
    HybridSearch -> DB [dir=back, label=" Fetch Chunks "];
    LLM -> User [label="Answer + Citations"];
    User -> Monitoring [label="Log Feedback"];
    Monitoring -> Grafana;
}
''', use_container_width=True)
