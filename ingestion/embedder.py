"""
Embedder — generates vector embeddings locally using sentence-transformers/all-MiniLM-L6-v2
via fastembed (ONNX Runtime under the hood, no PyTorch required).

Model specs:
  - Size: ~22MB ONNX file (downloads on first run, cached afterwards)
  - Output dimensions: 384
  - CPU inference: very fast (~100ms for 128 texts)
  - No GPU or CUDA required

Model is loaded once at module import time and reused across all calls.
"""
from fastembed import TextEmbedding

from ingestion.chunker import Chunk
from ingestion.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

# Load model once; fastembed downloads the ONNX file on first use (~22MB)
_model = TextEmbedding(model_name=EMBEDDING_MODEL)


def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    """
    Generate embeddings for a list of Chunk objects.
    Returns a list of float vectors in the same order as the input chunks.
    """
    texts = [chunk.content for chunk in chunks]
    return embed_texts(texts)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of raw strings.
    Returns a flat list of embedding vectors (each is list[float] of dim 384).
    """
    total = len(texts)
    print(f"[Embedder] Generating embeddings for {total} texts...")

    # fastembed.embed() returns a generator of numpy arrays
    embeddings = list(_model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE))
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
