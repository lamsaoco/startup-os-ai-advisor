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

# ── 1. CSS Injection for Mockup-Accurate Styling ──────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* Background & grid */
.stApp {
    background-color: #0b0c10;
    background-image:
        linear-gradient(rgba(124,58,237,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(124,58,237,0.03) 1px, transparent 1px);
    background-size: 30px 30px;
}
#MainMenu, footer, header { visibility: hidden; }

/* The main app container (simulating the mockup's window) */
.block-container { 
    padding-top: 0 !important; 
    padding-bottom: 80px !important;
    max-width: 1100px !important; 
}

/* Left Sidebar buttons (Pill shaped with outline) */
div[data-testid="stVerticalBlock"] > div > div > div > div > button {
    background: rgba(124,58,237,0.05) !important;
    border: 1px solid rgba(13, 148, 136, 0.4) !important;
    border-radius: 999px !important;
    color: #e2e8f0 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 10px 18px !important;
    margin-bottom: 8px !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.2s !important;
    box-shadow: 0 0 10px rgba(13, 148, 136, 0.05) !important;
}
div[data-testid="stVerticalBlock"] > div > div > div > div > button:hover {
    background: rgba(124,58,237,0.2) !important;
    border-color: #7c3aed !important;
    box-shadow: 0 0 15px rgba(124,58,237,0.3) !important;
    transform: translateY(-1px) !important;
}

/* Chat Input Styling */
.stChatInput {
    padding-bottom: 20px !important;
}
.stChatInputContainer {
    background: #1e1e2e !important;
    border: 1px solid rgba(124,58,237,0.4) !important;
    border-radius: 12px !important;
}
.stChatInputContainer textarea {
    color: #fff !important;
}
.stChatInputContainer button {
    background: linear-gradient(135deg, #7c3aed, #0d9488) !important;
    border-radius: 8px !important;
    border: none !important;
    color: white !important;
}

/* HTML Details/Summary for sources */
details {
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(124,58,237,0.2);
    border-radius: 8px;
    margin-top: 12px;
    padding: 8px 12px;
    font-size: 0.75rem;
}
summary {
    color: #a78bfa;
    cursor: pointer;
    font-weight: 600;
    outline: none;
}
.src-item {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.6);
}
.src-title { font-weight: 600; color: #cbd5e1; }
</style>
""", unsafe_allow_html=True)


# ── 2. Session state & Engine Init ──────────────────────────────────────────────
@st.cache_resource
def get_rag_engine():
    return RAGBase(use_reranker=True)

if "rag_engine"      not in st.session_state: st.session_state.rag_engine = get_rag_engine()
if "messages"        not in st.session_state: st.session_state.messages = []
if "last_log_id"     not in st.session_state: st.session_state.last_log_id = None
if "last_latency"    not in st.session_state: st.session_state.last_latency = None
if "pending_prompt"  not in st.session_state: st.session_state.pending_prompt = None


# ── 3. Top Gradient Banner ──────────────────────────────────────────────────────
st.markdown(
    f'<div style="background: linear-gradient(90deg, #7c3aed 0%, #0d9488 100%);'
    f'padding: 30px 40px; margin: 10px 0 20px; text-align: center; border-radius: 16px;'
    f'box-shadow: 0 4px 20px rgba(124,58,237,0.3);">'
    f'<p style="font-size:2rem; font-weight:700; color:#fff; margin:0; display:flex; align-items:center; justify-content:center; gap:10px;">'
    f'🚀 Startup OS AI Advisor</p>'
    f'<p style="font-size:1rem; color:rgba(255,255,255,0.9); margin:8px 0 0;">'
    f'AI-Powered Company Building Advisor</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Sub-header (Logo & Latency) ─────────────────────────────────────────────────
lat_html = ""
if st.session_state.last_latency:
    lat_html = f'<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:4px 12px; font-weight:600; color:#4ade80; font-size:0.85rem;">⚡ {st.session_state.last_latency:.1f}s</div>'

st.markdown(
    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding: 0 10px;">'
    f'<div style="display:flex; align-items:center; gap:12px;">'
    f'<div style="font-size:2rem;">🚀</div>'
    f'<div><div style="color:#fff; font-weight:600; font-size:1.1rem;">Startup OS</div><div style="color:rgba(255,255,255,0.5); font-size:0.8rem;">AI Advisor</div></div>'
    f'</div>'
    f'{lat_html}'
    f'</div>',
    unsafe_allow_html=True
)

# ── 4. Main Layout (Left: Pills, Right: Chat Card) ──────────────────────────────
QUICK_ACTIONS = [
    ("📋", "HR Policies"),
    ("🚀", "Hiring Process"),
    ("💰", "Compensation"),
    ("📈", "Performance Reviews")
]

left_col, right_col = st.columns([25, 75], gap="large")

with left_col:
    for icon, label in QUICK_ACTIONS:
        if st.button(f"{icon}  {label}", key=f"qa_{label}"):
            st.session_state.pending_prompt = f"Tell me about {label.lower()}"
            st.rerun()

    st.markdown('<div style="margin-top:30px;"></div>', unsafe_allow_html=True)
    if st.button("🗑️  Clear Chat", key="clear_chat"):
        st.session_state.messages = []
        st.session_state.last_log_id = None
        st.session_state.last_latency = None
        st.rerun()

with right_col:
    # Build the entire chat UI as a single HTML string so we can put it in a dark card
    chat_html = '<div style="background: #161622; border-radius: 16px; padding: 24px; min-height: 400px; border: 1px solid rgba(255,255,255,0.05);">'
    
    if not st.session_state.messages:
        chat_html += (
            '<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:300px; color:rgba(255,255,255,0.3);">'
            '<div style="font-size:2rem; margin-bottom:10px;">💬</div>'
            '<div>Select a topic on the left or type your question below.</div>'
            '</div>'
        )
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                content = str(msg["content"]).replace("<", "&lt;").replace(">", "&gt;")
                chat_html += (
                    f'<div style="display:flex; justify-content:flex-end; margin-bottom: 24px;">'
                    f'<div style="background: linear-gradient(135deg, #7c3aed, #2563eb); color: #fff; padding: 12px 20px; border-radius: 18px 18px 4px 18px; font-size: 0.9rem; max-width: 80%; box-shadow: 0 4px 15px rgba(124,58,237,0.3);">'
                    f'{content}'
                    f'</div></div>'
                )
            else:
                # Format AI markdown to basic HTML for rendering inside the block
                # (Since we are using unsafe_allow_html, basic tags like <br> work, but we'll just insert the text)
                content = str(msg["content"]).replace("\n", "<br>")
                
                # Render the glowing AI card with confidence meter
                chat_html += (
                    f'<div style="display:flex; margin-bottom: 24px;">'
                    f'<div style="background: #1e1e2e; border: 1px solid rgba(124,58,237,0.3); border-left: 4px solid #a855f7; border-radius: 8px 18px 18px 18px; padding: 16px 20px; max-width: 90%; box-shadow: -2px 0 15px rgba(168, 85, 247, 0.2);">'
                    f'<div style="color: #e2e8f0; font-size: 0.9rem; line-height: 1.6;">{content}</div>'
                )
                
                # Sources HTML details
                if msg.get("sources"):
                    chat_html += f'<details><summary>📚 View {len(msg["sources"])} Sources</summary>'
                    for i, chunk in enumerate(msg["sources"]):
                        chat_html += (
                            f'<div class="src-item">'
                            f'<div class="src-title">[{i+1}] {chunk.get("heading_path", "Section")}</div>'
                            f'<div style="font-size:0.65rem; color:rgba(255,255,255,0.4); margin-bottom:4px;">{chunk.get("breadcrumb", "")}</div>'
                            f'<div>{str(chunk.get("content", ""))[:200]}...</div>'
                            f'</div>'
                        )
                    chat_html += '</details>'
                
                # Confidence meter
                confidence_width = "85%" # Mock value for aesthetics
                chat_html += (
                    f'<div style="margin-top: 16px; display:flex; align-items:center; gap:12px; font-size:0.75rem; color:rgba(255,255,255,0.5);">'
                    f'<div>Confidence meter</div>'
                    f'<div style="flex:1; height:6px; background:rgba(0,0,0,0.3); border-radius:3px; overflow:hidden;">'
                    f'<div style="width:{confidence_width}; height:100%; background:linear-gradient(90deg, #7c3aed, #0d9488);"></div>'
                    f'</div>'
                    f'</div>'
                )
                
                chat_html += '</div></div>'

    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)
    
    # Feedback
    if st.session_state.last_log_id:
        fb1, fb2, _ = st.columns([1, 1, 6])
        with fb1:
            if st.button("👍 Helpful", key="fb_up"):
                log_feedback(st.session_state.last_log_id, 1)
                st.session_state.last_log_id = None
                st.rerun()
        with fb2:
            if st.button("👎 Not Helpful", key="fb_down"):
                log_feedback(st.session_state.last_log_id, -1)
                st.session_state.last_log_id = None
                st.rerun()

# ── 5. Global Chat Input ────────────────────────────────────────────────────────
prompt = st.chat_input("Send a message...")

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("🔍 Searching..."):
        try:
            result          = st.session_state.rag_engine.run(prompt)
            answer          = result["answer"]
            chunks          = result["retrieved_chunks"]
            latency         = result["latency_seconds"]
            rewritten_query = result["rewritten_query"]

            st.session_state.last_latency = latency

            log_id = log_interaction(
                user_query=prompt,
                rewritten_query=rewritten_query,
                retrieved_chunks=chunks,
                llm_response=answer,
                latency_seconds=latency,
            )
            st.session_state.last_log_id = log_id
            st.session_state.messages.append({
                "role": "assistant", "content": answer,
                "sources": chunks,  "latency": latency,
            })

        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"⚠️ Error: {str(e)}",
                "sources": [],
            })

    st.rerun()
