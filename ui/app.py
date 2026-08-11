import streamlit as st
import time
from dotenv import load_dotenv

st.set_page_config(
    page_title="Startup OS AI Advisor",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_dotenv()

from retrieval.rag_base import RAGBase
from ui.logger import log_interaction, log_feedback

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
header, footer, #MainMenu {
    visibility: hidden !important;
    display: none !important;
}
.stApp {
    background-color: #0d1117 !important;
    background-image: 
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 20px 20px;
    color: #c9d1d9;
}
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px !important;
}

/* 2. Phần Header (Top Banner) */
.top-banner {
    background: linear-gradient(90deg, #8b5cf6 0%, #0d9488 100%);
    border-radius: 12px;
    padding: 15px 30px;
    text-align: center;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 5px 15px rgba(139, 92, 246, 0.2);
}
.banner-title {
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}
.banner-subtitle {
    font-size: 0.95rem;
    font-weight: 300;
    margin-top: 5px;
    opacity: 0.9;
}

/* 3. Bố cục chính (Main Layout) */
div[data-testid="stHorizontalBlock"] {
    background-color: rgba(22, 27, 34, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}

/* 4. Cột Trái (Left Column) */
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

/* Nút chức năng hình viên thuốc */
/* Target all buttons in the first column forcefully */
div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
    background-color: #21262d !important;
    background: #21262d !important;
    border: 1px solid rgba(6, 182, 212, 0.5) !important;
    border-radius: 50px !important;
    color: #e6edf3 !important;
    padding: 8px 15px !important;
    width: 100% !important;
    text-align: left !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    margin-bottom: 8px !important;
    transition: all 0.3s ease !important;
    display: flex !important;
    justify-content: flex-start !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(1) button * {
    color: #e6edf3 !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(1) button:hover {
    background-color: #30363d !important;
    background: #30363d !important;
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.4) !important;
    border-color: #06b6d4 !important;
    transform: translateY(-2px) !important;
}

/* 5. Cột Phải (Right Column) & Chat Interface */
.chat-container {
    background-color: #0d1117;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 15px;
    min-height: 500px;
    max-height: 650px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 15px;
}

/* Welcome Message Native */
div[data-testid="column"]:nth-child(2) button[kind="primary"] {
    background: rgba(139, 92, 246, 0.1) !important;
    border: 1px solid rgba(139, 92, 246, 0.4) !important;
    color: #a855f7 !important;
    border-radius: 20px !important;
    padding: 10px !important;
    font-size: 0.95rem !important;
    margin-bottom: 10px !important;
    transition: 0.3s !important;
}
div[data-testid="column"]:nth-child(2) button[kind="primary"] * {
    color: #a855f7 !important;
}
div[data-testid="column"]:nth-child(2) button[kind="primary"]:hover {
    background: rgba(139, 92, 246, 0.3) !important;
    box-shadow: 0 0 15px rgba(139, 92, 246, 0.4) !important;
    transform: translateY(-2px) !important;
}

/* Feedback Buttons */
div[data-testid="column"]:nth-child(2) button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #8b949e !important;
    border-radius: 8px !important;
}
div[data-testid="column"]:nth-child(2) button[kind="secondary"] * {
    color: #8b949e !important;
}
div[data-testid="column"]:nth-child(2) button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    color: #e6edf3 !important;
}

/* User Message */
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
}

/* AI Message */
.msg-ai {
    align-self: flex-start;
    background-color: #161b22;
    color: #e6edf3;
    padding: 15px 20px;
    border-radius: 8px 18px 18px 18px;
    max-width: 90%;
    font-size: 0.95rem;
    line-height: 1.6;
    border: 1px solid rgba(255,255,255,0.05);
    border-left: 4px solid #d946ef;
    box-shadow: -4px 0 20px rgba(217, 70, 239, 0.2);
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
    flex-grow: 1;
    height: 4px;
    background-color: #21262d;
    border-radius: 2px;
    overflow: hidden;
}
.confidence-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #d946ef, #0ea5e9);
    border-radius: 2px;
}

/* Sources inside AI message */
details.sources {
    margin-top: 12px;
    background: rgba(0,0,0,0.2);
    padding: 10px;
    border-radius: 8px;
    border: 1px solid rgba(217, 70, 239, 0.2);
    font-size: 0.8rem;
}
details.sources summary {
    color: #d946ef; cursor: pointer; font-weight: 600;
}
details.sources .src-item {
    margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(255,255,255,0.1);
}

/* 6. Khu vực nhập tin nhắn (Input Area) */
div[data-testid="stForm"] {
    background-color: #161b22 !important;
    border: 1px solid #a855f7 !important;
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.4) !important;
    border-radius: 12px !important;
    padding: 5px !important;
    margin-top: 15px !important;
}
div[data-testid="stTextInput"] div[data-baseweb="input"] {
    background-color: #0d1117 !important;
    border: none !important;
    border-radius: 8px !important;
}
div[data-testid="stTextInput"] input {
    color: #e6edf3 !important;
    background-color: #0d1117 !important;
    font-size: 0.95rem !important;
}
div[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(90deg, #8b5cf6, #14b8a6) !important;
    border: none !important;
    border-radius: 8px !important;
    color: white !important;
    font-weight: 700 !important;
    height: 100% !important;
    min-height: 40px !important;
    width: 100% !important;
    transition: 0.3s !important;
}
div[data-testid="stFormSubmitButton"] button * {
    color: white !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
    box-shadow: 0 0 15px rgba(20, 184, 166, 0.5) !important;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. Session State & Engine Init
# ==========================================
@st.cache_resource
def get_rag_engine():
    return RAGBase(use_reranker=True)

if "messages"        not in st.session_state: st.session_state.messages = []
if "last_log_id"     not in st.session_state: st.session_state.last_log_id = None
if "last_latency"    not in st.session_state: st.session_state.last_latency = None
if "pending_prompt"  not in st.session_state: st.session_state.pending_prompt = None
if "is_processing"   not in st.session_state: st.session_state.is_processing = False


# ==========================================
# 3. Phần Header (Top Banner)
# ==========================================
st.markdown("""
<div class="top-banner">
    <h1 class="banner-title">🚀 Startup OS AI Advisor</h1>
    <p class="banner-subtitle">AI-Powered Company Building Advisor</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 4 & 5. Bố cục chính (Main Layout)
# ==========================================
# Thu gọn cột trái (20%) để tối đa diện tích chat (80%)
left_col, right_col = st.columns([20, 80], gap="medium")

with left_col:
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
        <div class="latency-badge">{lat_text}</div>
    </div>
    """, unsafe_allow_html=True)

    # Nút chức năng
    if st.button("📋 HR Policies"): st.session_state.pending_prompt = "Tell me about HR policies"
    if st.button("🚀 Hiring Process"): st.session_state.pending_prompt = "Tell me about the Hiring Process"
    if st.button("💰 Compensation"): st.session_state.pending_prompt = "How does Compensation work?"
    if st.button("📈 Performance Reviews"): st.session_state.pending_prompt = "Explain Performance Reviews"
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.last_log_id = None
        st.session_state.last_latency = None
        st.rerun()


with right_col:
    # --- CHAT AREA ---
    chat_placeholder = st.empty()
    
    if not st.session_state.messages:
        # Sử dụng Native Container cho giao diện trống để các nút có thể click được
        with chat_placeholder.container():
            st.markdown("""
            <div style="text-align: center; margin-top: 40px; margin-bottom: 30px;">
                <h2 style="color: #e6edf3; font-size: 1.8rem; margin-bottom: 10px;">👋 Hello! I am your Startup OS AI Advisor</h2>
                <p style="color: #8b949e; font-size: 1rem;">Ask me anything about HR, Operations, or Company Building.</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 6, 1])
            with c2:
                if st.button("What is the remote work policy?", type="primary", use_container_width=True):
                    st.session_state.pending_prompt = "What is the remote work policy?"
                    st.rerun()
                if st.button("How do I request a new laptop?", type="primary", use_container_width=True):
                    st.session_state.pending_prompt = "How do I request a new laptop?"
                    st.rerun()
                if st.button("Explain the performance review cycle", type="primary", use_container_width=True):
                    st.session_state.pending_prompt = "Explain the performance review cycle"
                    st.rerun()
            
            st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)
    else:
        html_chat = '<div class="chat-container">'
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                content = str(msg["content"]).replace("<", "&lt;").replace(">", "&gt;")
                html_chat += f'<div class="msg-user">{content}</div>'
            else:
                content = str(msg["content"]).replace("\n", "<br>")
                html_chat += f'<div class="msg-ai">{content}'
                
                # Sources
                if msg.get("sources"):
                    html_chat += f'<details class="sources"><summary>📚 View {len(msg["sources"])} Sources</summary>'
                    for i, chunk in enumerate(msg["sources"]):
                        html_chat += f'<div class="src-item"><b>[{i+1}] {chunk.get("heading_path", "Section")}</b><br><span style="opacity:0.6">{chunk.get("breadcrumb", "")}</span><br>{str(chunk.get("content", ""))[:200]}...</div>'
                    html_chat += '</details>'
                
                # Confidence Meter
                html_chat += f"""
                <div class="confidence-meter">
                    <span>Confidence meter</span>
                    <div class="confidence-bar-bg"><div class="confidence-bar-fill" style="width: 92%;"></div></div>
                </div>
                </div>
                """
        html_chat += '</div>'
        chat_placeholder.markdown(html_chat, unsafe_allow_html=True)
    
    # Feedback
    if st.session_state.last_log_id:
        c1, c2, _ = st.columns([2, 2, 8])
        with c1:
            if st.button("👍 Helpful"):
                log_feedback(st.session_state.last_log_id, 1)
                st.session_state.last_log_id = None
                st.rerun()
        with c2:
            if st.button("👎 Not Helpful"):
                log_feedback(st.session_state.last_log_id, -1)
                st.session_state.last_log_id = None
                st.rerun()

    # --- INPUT AREA ---
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([85, 15])
        with col_input:
            prompt_input = st.text_input("Message", label_visibility="collapsed", placeholder="Type your message here...")
        with col_btn:
            submitted = st.form_submit_button("Send")


# ==========================================
# 6. Process Input
# ==========================================
prompt = None
if submitted and prompt_input:
    prompt = prompt_input
elif st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.is_processing = True
    
    # Render the user message immediately by re-building the HTML chat (before LLM runs)
    immediate_html_chat = '<div class="chat-container">'
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            c = str(msg["content"]).replace("<", "&lt;").replace(">", "&gt;")
            immediate_html_chat += f'<div class="msg-user">{c}</div>'
        else:
            c = str(msg["content"]).replace("\n", "<br>")
            immediate_html_chat += f'<div class="msg-ai">{c}</div>'
    immediate_html_chat += '</div>'
    chat_placeholder.markdown(immediate_html_chat, unsafe_allow_html=True)

    spinner_msg = "🔍 Khởi động AI Engine (Chỉ mất vài giây ở lần đầu tiên)..." if "rag_engine" not in st.session_state else "🔍 Searching knowledge base..."
    
    # Đặt spinner TRONG khung chat (cột phải) bằng cách dùng right_col container
    with right_col:
        with st.spinner(spinner_msg):
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
