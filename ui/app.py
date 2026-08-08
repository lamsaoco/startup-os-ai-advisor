import streamlit as st
import time

# Page config must be the very first Streamlit command
st.set_page_config(
    page_title="Startup OS AI Advisor",
    page_icon="✨",
    layout="centered"
)

from dotenv import load_dotenv
load_dotenv()

from retrieval.rag_base import RAGBase
from ui.logger import log_interaction, log_feedback

# --- 1. Load Custom CSS ---
def load_css():
    with open("ui/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# --- 2. Initialize App State ---
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGBase()

if "messages" not in st.session_state:
    # Initial welcome message
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to Startup OS! I am your AI Operations & HR Advisor. Ask me anything about company building, policies, or management frameworks."}
    ]

if "last_log_id" not in st.session_state:
    st.session_state.last_log_id = None

# --- 3. UI Header ---
st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>✨ Startup OS Advisor</h1>", unsafe_allow_html=True)

# --- 4. Render Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # If there are sources attached to an assistant message, show them in an expander
        if "sources" in msg and msg["sources"]:
            with st.expander("📚 View Citations"):
                for idx, chunk in enumerate(msg["sources"]):
                    st.markdown(f"**[{idx+1}] {chunk['breadcrumb']} > {chunk['heading_path']}**")
                    st.caption(f"_{chunk['content'][:200]}..._")

# --- 5. User Input ---
if prompt := st.chat_input("Ask a question (e.g., 'How do we handle performance reviews?'):"):
    # Append and render user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Run RAG Pipeline
                result = st.session_state.rag_engine.run(prompt)
                
                answer = result["answer"]
                chunks = result["retrieved_chunks"]
                latency = result["latency_seconds"]
                rewritten_query = result["rewritten_query"]
                
                # Render answer
                st.markdown(answer)
                
                # Render sources
                if chunks:
                    with st.expander(f"📚 Citations & Sources (Retrieved in {latency:.2f}s)"):
                        for idx, chunk in enumerate(chunks):
                            st.markdown(f"**[{idx+1}] {chunk.get('breadcrumb', 'Doc')} > {chunk.get('heading_path', 'Root')}**")
                            st.caption(f"_{chunk['content'][:200]}..._")
                            
                # Log interaction to Postgres
                log_id = log_interaction(
                    user_query=prompt,
                    rewritten_query=rewritten_query,
                    retrieved_chunks=chunks,
                    llm_response=answer,
                    latency_seconds=latency
                )
                
                # Update session state with the new message and log ID
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": chunks
                })
                st.session_state.last_log_id = log_id
                
            except Exception as e:
                st.error(f"Error connecting to RAG engine: {str(e)}")

# --- 6. Feedback Buttons (Only show for the latest response) ---
if st.session_state.last_log_id:
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if st.button("👍 Helpful"):
            log_feedback(st.session_state.last_log_id, 1)
            st.success("Thanks for the feedback!")
            st.session_state.last_log_id = None # hide buttons after voting
            st.rerun()
    with cols[1]:
        if st.button("👎 Not Helpful"):
            log_feedback(st.session_state.last_log_id, -1)
            st.warning("Thanks, we will improve.")
            st.session_state.last_log_id = None # hide buttons after voting
            st.rerun()
