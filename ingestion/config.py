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
EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # Local ONNX (~1GB)
EMBEDDING_DIMENSIONS: int = 768              # Output dimension of mpnet

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "startup_os")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")

# ── Chunking ─────────────────────────────────────────────────────────────────
CHUNK_MAX_TOKENS: int = 450  # Split further if a section exceeds this limit
CHUNK_MIN_TOKENS: int = 50   # Merge with next chunk if smaller than this

# ── Embedding batch ──────────────────────────────────────────────────────────
EMBEDDING_BATCH_SIZE: int = 128  # Chunks per local model batch (MiniLM is fast on CPU)
