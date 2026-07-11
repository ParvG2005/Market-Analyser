"""Local sentence-transformers embeddings (bge-small-en, 384-dim)."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("BAAI/bge-small-en")


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True).tolist()
