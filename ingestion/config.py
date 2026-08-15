"""
Centralized configuration — reads all environment variables from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Notion ───────────────────────────────────────────────────────────────────
NOTION_API_KEY: str = os.environ["NOTION_API_KEY"]
# Root page ID extracted from the Notion page URL (32-char hex at the end)
NOTION_ROOT_PAGE_ID: str = os.environ["NOTION_ROOT_PAGE_ID"]

# ── Gemini via OpenAI-compatible endpoint ────────────────────────────────────
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
CHAT_MODEL: str = "gemini-3.1-flash-lite"   # Used for query rewriting & generation (via OpenAI SDK)
EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"    # Local ONNX via fastembed (~1.3GB, best English MTEB ~54.3)
EMBEDDING_DIMENSIONS: int = 1024             # Output dimension of bge-large-en-v1.5
CROSS_ENCODER_MODEL: str = "BAAI/bge-reranker-base" # Local ONNX for reranking

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "startup_os")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")

# ── Chunking ─────────────────────────────────────────────────────────────────
CHUNK_MAX_TOKENS: int = 512   # Split further if a section exceeds this limit
CHUNK_MIN_TOKENS: int = 50    # Merge with next chunk if smaller than this
CHUNK_OVERLAP_TOKENS: int = 64 # Token overlap between consecutive paragraph sub-chunks

# ── Embedding batch ──────────────────────────────────────────────────────────
EMBEDDING_BATCH_SIZE: int = 128  # Chunks per local model batch (MiniLM is fast on CPU)

# ── Retrieval & Reranking ────────────────────────────────────────────────────
RETRIEVAL_TOP_K: int = 8         # Reduced to 8 to avoid slow CPU reranking (16 max candidates)
RERANK_TOP_K: int = 3           # Reduced to 3 for faster LLM processing
