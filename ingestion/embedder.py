"""
Model is loaded once at module import time and reused across all calls.
"""
from fastembed import TextEmbedding
from tqdm import tqdm

from ingestion.chunker import Chunk
from ingestion.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

# Load model once; fastembed downloads the ONNX file on first use (~900MB)
# Cache is stored in the mounted ./data volume so it persists across container restarts.
# HF_HOME must also point here (set in docker-compose) so huggingface_hub
# internal temp files don't end up in ~/.cache which may be unwritable.
import os

# Fallback to local project data dir when running outside Docker.
# Docker containers should set FASTEMBED_CACHE_DIR via docker-compose env.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.getenv("FASTEMBED_CACHE_DIR", os.path.join(_project_root, "data", ".model_cache"))
_model = TextEmbedding(model_name=EMBEDDING_MODEL, cache_dir=CACHE_DIR)


def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    """
    Generate embeddings for a list of Chunk objects.
    Uses chunk.embed_text (breadcrumb + heading_path + content) so the
    vector index captures full document hierarchy, not just bare text.
    Returns a list of float vectors in the same order as the input chunks.
    """
    texts = [chunk.embed_text for chunk in chunks]
    return embed_texts(texts)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of raw strings.
    Returns a flat list of embedding vectors (each is list[float] of dim 384).
    """
    total = len(texts)
    print(f"[Embedder] Generating embeddings for {total} texts...")

    # fastembed.embed() returns a generator of numpy arrays
    embeddings = list(tqdm(_model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE), total=total, desc="Embedding texts", unit="chunk"))
    result = [emb.tolist() for emb in embeddings]

    print(f"[Embedder] Done — {len(result)} embeddings generated (dim={len(result[0]) if result else 0})")
    return result


def embed_query(query: str) -> list[float]:
    """
    Generate a single embedding for a user query at inference time.
    Returns a single float vector of dim 384.
    """
    embeddings = list(_model.embed([query]))
    return embeddings[0].tolist()
