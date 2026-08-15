import streamlit as st
import time
from dotenv import load_dotenv

st.set_page_config(
    page_title="Startup OS AI Advisor",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()

from retrieval.rag_base import RAGBase
from ui.logger import log_interaction, log_feedback
import streamlit.components.v1 as components

# ==========================================
# 1. Cấu hình chung (General Styling) & CSS
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

/* Reset and general */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}
footer, #MainMenu {
    visibility: hidden !important;
    display: none !important;
}

/* =============================================================
   LAYOUT ENGINE
============================================================= */
.stApp {
    background-color: #09090b;
    background-image: 
        linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
    background-size: 30px 30px;
    color: #c9d1d9;
}
.block-container {
    padding: 3rem 1rem 1rem 1rem !important;
    max-width: 100% !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #09090b !important;
    border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
}



/* Sidebar Nav Buttons Styling */

[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button {
    background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
    border-radius: 10px !important;
    padding: 12px 15px !important;
    margin-bottom: 10px !important;
    color: #e6edf3 !important;
    font-weight: 500 !important;
    display: block !important;
    text-align: left !important;
    width: 100% !important;
    transition: all 0.3s ease !important;
}
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button:hover {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(13, 148, 136, 0.1)) !important;
    border: 1px solid rgba(139, 92, 246, 0.4) !important;
    color: #fff !important;
    box-shadow: 0 6px 15px rgba(139, 92, 246, 0.2) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button p { 
    margin: 0 !important; 
    color: inherit !important; 
    text-align: left !important; 
    display: block !important;
    width: 100% !important;
}


/* -----------------------------------------
   4. Left Navigator Panel Styles
----------------------------------------- */
.left-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.left-logo {
    display: flex;
    align-items: center;
    gap: 10px;
}
.left-logo span.icon { font-size: 1.5rem; }
.left-logo-text { line-height: 1.2; }
.left-logo-text .main { font-weight: 700; font-size: 1rem; color: #fff; }
.left-logo-text .sub { font-size: 0.75rem; color: #8b949e; }
.latency-badge {
    background: #21262d;
    color: #3fb950;
    padding: 4px 8px;
    border-radius: 8px;
    font-size: 0.7rem;
    font-weight: 600;
    border: 1px solid rgba(63, 185, 80, 0.3);
}

/* -----------------------------------------
   Dynamic Chat Container
----------------------------------------- */
/* Fix markdown list spacing */
.msg-ai ul, .msg-ai ol { margin-top: 0.5em; margin-bottom: 0.5em; padding-left: 1.5em; }
.msg-ai p { margin-bottom: 0.5em; }

/* Empty State Wrapper */
.empty-state-text { text-align: center; padding: 20px 0; }

/* -----------------------------------------
   Button System via ID Markers
----------------------------------------- */
button {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    transition: all 0.25s ease !important;
    cursor: pointer !important;
    width: 100% !important;
}

/* 1. New Conversation Button */
div.element-container:has(#new-chat-btn) + div.element-container button {
    background: linear-gradient(135deg, #6d28d9, #0d9488) !important;
    color: #fff !important;
    padding: 10px 16px !important;
    border: none !important;
}
div.element-container:has(#new-chat-btn) + div.element-container button:hover {
    box-shadow: 0 4px 15px rgba(13, 148, 136, 0.4) !important;
    transform: translateY(-1px) !important;
}

/* 2. Left Navigator Topic Buttons */
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 6px !important;
    padding: 8px 10px !important;
    color: #8b949e !important;
    font-weight: 400 !important;
    display: block !important;
    text-align: left !important;
    width: 100% !important;
}
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #e6edf3 !important;
}
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button > div {
    display: block !important;
    width: 100% !important;
    text-align: left !important;
}
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#nav-topic-btns) button p { 
    margin: 0 !important; 
    color: inherit !important; 
    text-align: left !important; 
    display: block !important;
    width: 100% !important;
}

/* 3. Empty State Suggestion Buttons */
div[data-testid="stVerticalBlock"]:has(#empty-state-btns) div.stButton {
    display: flex;
    justify-content: center;
}
div[data-testid="stVerticalBlock"]:has(#empty-state-btns) button {
    background-color: transparent !important;
    border: 1px solid rgba(6, 182, 212, 0.35) !important;
    border-radius: 20px !important;
    color: #c9d1d9 !important;
    padding: 8px 20px !important;
    text-align: center !important;
    justify-content: center !important;
    width: fit-content !important;
    margin: 0 auto !important;
}
div[data-testid="stVerticalBlock"]:has(#empty-state-btns) button:hover {
    background-color: rgba(6, 182, 212, 0.1) !important;
    border-color: #06b6d4 !important;
    color: #e6edf3 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(6, 182, 212, 0.2) !important;
}

/* 4. Feedback Buttons (Helpful/Not Helpful) */
div[data-testid="stVerticalBlock"]:has(#feedback-btns) button {
    background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 20px !important;
    color: #c9d1d9 !important;
    padding: 6px 16px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
    transition: all 0.3s ease !important;
    width: 140px !important;
}
div[data-testid="stVerticalBlock"]:has(#feedback-btns) button:hover {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(13, 148, 136, 0.15)) !important;
    color: #fff !important;
    border-color: rgba(139, 92, 246, 0.5) !important;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
    transform: translateY(-2px) !important;
}

/* -----------------------------------------
   Chat Messages

----------------------------------------- */
.msg-user {
    align-self: flex-end;
    background: linear-gradient(135deg, #a855f7 0%, #3b82f6 100%);
    color: white;
    padding: 12px 18px;
    border-radius: 18px 18px 4px 18px;
    max-width: 80%;
    font-size: 0.95rem;
    line-height: 1.5;
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
    margin-bottom: 15px;
    margin-left: auto;
    width: fit-content;
}
.msg-ai {
    align-self: flex-start;
    background-color: #18181b;
    color: #e6edf3;
    padding: 15px 20px;
    border-radius: 8px 18px 18px 18px;
    max-width: 90%;
    font-size: 0.95rem;
    line-height: 1.6;
    border: 1px solid rgba(255,255,255,0.05);
    border-left: 4px solid #d946ef;
    box-shadow: -4px 0 20px rgba(217, 70, 239, 0.2);
    margin-bottom: 15px;
}
.confidence-meter {
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.75rem;
    color: #8b949e;
}
.confidence-bar-bg {
    flex-grow: 1; height: 4px; background-color: #21262d; border-radius: 2px; overflow: hidden;
}
.confidence-bar-fill {
    height: 100%; background: linear-gradient(90deg, #d946ef, #0ea5e9); border-radius: 2px;
}
details.sources {
    margin-top: 12px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;
    border: 1px solid rgba(217, 70, 239, 0.2); font-size: 0.8rem;
}
details.sources summary { color: #d946ef; cursor: pointer; font-weight: 600; }
details.sources .src-item { margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(255,255,255,0.1); }

/* Custom Spinner */
.spinner-css {
    width: 20px; height: 20px; border: 3px solid rgba(217, 70, 239, 0.3);
    border-radius: 50%; border-top-color: #d946ef; animation: spin 1s ease-in-out infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* -----------------------------------------
   Input Area (st.chat_input) Elegant Styling
----------------------------------------- */
div[data-testid="stChatInput"],
div[data-testid="stChatInput"] > div,
div[data-testid="stChatInput"] div[data-baseweb],
div[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
}
div[data-testid="stChatInput"] {
    border: 1px solid rgba(139, 92, 246, 0.4) !important;
    border-radius: 12px !important;
}
div[data-testid="stChatInput"] textarea {
    color: white !important;
}
div[data-testid="stChatInput"] button {
    background: linear-gradient(90deg, #8b5cf6, #14b8a6) !important;
    border-radius: 8px !important;
}
div[data-testid="stChatInput"] button svg {
    fill: white !important;
}
div[data-testid="stChatInput"] button:hover {
    box-shadow: 0 0 15px rgba(20, 184, 166, 0.4) !important;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. Session State & Engine Init
# ==========================================
import threading

@st.cache_resource(show_spinner=False)
def get_rag_engine():
    engine = RAGBase(use_reranker=True)
    # Warm up models to eliminate cold-start latency on first chat
    try:
        from ingestion.embedder import embed_query
        _ = embed_query("warmup")
        if getattr(engine, "_cross_encoder", None):
            engine._cross_encoder.predict([["warmup", "warmup"]])
    except Exception as e:
        print(f"Warmup error: {e}")
    return engine

# Eager Pre-loading in main thread to ensure chat is fast (blocks first page load)
if "engine_warmup_started" not in st.session_state:
    st.session_state.engine_warmup_started = True
    get_rag_engine()

if "messages"        not in st.session_state: st.session_state.messages = []
if "last_log_id"     not in st.session_state: st.session_state.last_log_id = None
if "last_latency"    not in st.session_state: st.session_state.last_latency = None
if "pending_prompt"  not in st.session_state: st.session_state.pending_prompt = None
if "is_processing"   not in st.session_state: st.session_state.is_processing = False


# ==========================================
# 3. Phần Header (Top Banner)
# ==========================================
st.title("🚀 Startup OS AI Advisor")


# ==========================================
# 4. Giao diện Sidebar & Chat (Layout)
# ==========================================

with st.sidebar:
    # Header cột trái (Logo & Badge)
    lat_text = f"⚡ {st.session_state.last_latency:.1f}s" if st.session_state.last_latency else "⚡ --s"
    st.markdown(f"""
    <div class="left-header">
        <div class="left-logo">
            <span class="icon">🚀</span>
            <div class="left-logo-text">
                <div class="main">Startup OS</div>
                <div class="sub">AI Advisor</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Nút chức năng
    st.markdown('<div id="new-chat-btn"></div>', unsafe_allow_html=True)
    if st.button("✨ New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_log_id = None
        st.session_state.last_latency = None
        st.rerun()
        
    st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)

    topic_container = st.container()
    with topic_container:
        st.markdown('<div id="nav-topic-btns"></div>', unsafe_allow_html=True)
        if st.button("📋 HR Policies", use_container_width=True): st.session_state.pending_prompt = "Tell me about HR policies"
        if st.button("🚀 Hiring Process", use_container_width=True): st.session_state.pending_prompt = "Tell me about the Hiring Process"
        if st.button("💰 Compensation", use_container_width=True): st.session_state.pending_prompt = "How does Compensation work?"
        if st.button("📈 Performance Reviews", use_container_width=True): st.session_state.pending_prompt = "Explain Performance Reviews"


with st.container():
    # --- CHAT AREA ---
    chat_wrapper = st.container()
    
    if not st.session_state.messages:
        with chat_wrapper:
            st.markdown('<div id="chat-wrapper-marker"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="empty-state-text">
                <h2 style="color: #e6edf3; font-size: 1.8rem; margin-bottom: 10px;">👋 Hello! I am your Startup OS AI Advisor</h2>
                <p style="color: #8b949e; font-size: 1rem;">Ask me anything about HR, Operations, or Company Building.</p>
            </div>
            """, unsafe_allow_html=True)
            
            empty_container = st.container()
            with empty_container:
                st.markdown('<div id="empty-state-btns"></div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 6, 1])
                with c2:
                    if st.button("What is the remote work policy?", use_container_width=True):
                        st.session_state.pending_prompt = "What is the remote work policy?"
                        st.rerun()
                    if st.button("How do I request a new laptop?", use_container_width=True):
                        st.session_state.pending_prompt = "How do I request a new laptop?"
                        st.rerun()
                    if st.button("Explain the performance review cycle", use_container_width=True):
                        st.session_state.pending_prompt = "Explain the performance review cycle"
                        st.rerun()
    else:
        with chat_wrapper:
            st.markdown('<div id="chat-wrapper-marker"></div>', unsafe_allow_html=True)
            import markdown_it
            md = markdown_it.MarkdownIt()
            
            for msg in st.session_state.messages:
                html_chat = ''
                if msg["role"] == "user":
                    content = str(msg["content"]).replace("<", "&lt;").replace(">", "&gt;")
                    html_chat += f'<div class="msg-user">{content}</div>'
                    st.markdown(html_chat, unsafe_allow_html=True)
                else:
                    content_html = md.render(str(msg["content"]))
                    html_chat += f'<div class="msg-ai">{content_html}'
                    
                    # Sources
                    if msg.get("sources"):
                        html_chat += f'<details class="sources"><summary>📚 View {len(msg["sources"])} Sources</summary>'
                        for i, chunk in enumerate(msg["sources"]):
                            html_chat += f'<div class="src-item"><b>[{i+1}] {chunk.get("heading_path", "Section")}</b><br><span style="opacity:0.6">{chunk.get("breadcrumb", "")}</span><br>{str(chunk.get("content", ""))[:200]}...</div>'
                        html_chat += '</details>'
                    
                    # Confidence Meter and Latency
                    latency_text = f'⚡ {msg["latency"]:.1f}s' if msg.get("latency") else ''
                    html_chat += f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                        <div class="confidence-meter" style="margin-top: 0;">
                            <span>Confidence meter</span>
                            <div class="confidence-bar-bg"><div class="confidence-bar-fill" style="width: 92%;"></div></div>
                        </div>
                        <div style="font-size: 0.8rem; color: #06b6d4; font-weight: 600;">{latency_text}</div>
                    </div>
                    </div>
                    """
                    st.markdown(html_chat, unsafe_allow_html=True)
                    
                    # Add Feedback Buttons directly below the message if it has a log_id
                    log_id = msg.get("log_id")
                    if log_id:
                        if not msg.get("feedback"):
                            c1, c2, _ = st.columns([1.5, 1.5, 9])
                            with c1:
                                if st.button("👍 Helpful", key=f"up_{log_id}"):
                                    log_feedback(log_id, 1)
                                    msg["feedback"] = 1
                                    st.rerun()
                            with c2:
                                if st.button("👎 Not Helpful", key=f"down_{log_id}"):
                                    log_feedback(log_id, -1)
                                    msg["feedback"] = -1
                                    st.rerun()
                        else:
                            st.caption("✨ Cảm ơn bạn đã đánh giá!")

    # --- INPUT AREA ---
    # Handled natively by st.chat_input below

# ==========================================
# Auto-Scroll & Dynamic Container JS
# ==========================================
# Removed manual scroll hack to favor native Streamlit scrolling

# ==========================================
# 6. Process Input
# ==========================================
prompt_input = st.chat_input("Type your message here...")

prompt = None
if prompt_input:
    prompt = prompt_input
elif st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.is_processing = True
    
    spinner_msg = "Starting AI Engine (Takes a few seconds initially)..." if "rag_engine" not in st.session_state else "Searching knowledge base..."
    
    # Render the user message AND the custom spinner immediately in the chat wrapper
    with chat_wrapper:
        immediate_html_chat = ''
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                c = str(msg["content"]).replace("<", "&lt;").replace(">", "&gt;")
                immediate_html_chat += f'<div class="msg-user">{c}</div>'
            else:
                c = str(msg["content"]).replace("\n", "<br>")
                immediate_html_chat += f'<div class="msg-ai">{c}</div>'
        
        # Custom Animated Bubble Spinner
        immediate_html_chat += f'''
        <div class="msg-ai" style="opacity: 0.8; display: flex; align-items: center; gap: 12px; padding: 12px 20px;">
            <div class="spinner-css"></div>
            <span style="color: #a855f7; font-weight: 600;">{spinner_msg}</span>
        </div>
        '''
        st.markdown(immediate_html_chat, unsafe_allow_html=True)

    try:
        if "rag_engine" not in st.session_state:
            st.session_state.rag_engine = get_rag_engine()
            
        result          = st.session_state.rag_engine.run(prompt)
        answer          = result["answer"]
        chunks          = result["retrieved_chunks"]
        latency         = result["latency_seconds"]
        rewritten_query = result["rewritten_query"]

        st.session_state.last_latency = latency
        log_id = log_interaction(
            user_query=prompt, rewritten_query=rewritten_query,
            retrieved_chunks=chunks, llm_response=answer, latency_seconds=latency,
        )
        st.session_state.last_log_id = log_id
        st.session_state.messages.append({
            "role": "assistant", "content": answer,
            "sources": chunks, "latency": latency,
        })

    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant", "content": f"⚠️ Error: {str(e)}", "sources": [],
        })
    
    st.session_state.is_processing = False
    st.rerun()
