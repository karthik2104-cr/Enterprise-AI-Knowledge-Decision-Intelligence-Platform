from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.core.config import get_settings

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed bag-of-words embeddings for local/demo mode."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            vec[idx] += 1.0
            idx2 = int.from_bytes(digest[4:8], "big") % self.dim
            vec[idx2] += 0.5
        return l2_normalize(vec)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dim: int):
        self.api_key = api_key
        self.model = model
        self.dim = dim
        self._fallback = HashingEmbeddingProvider(dim)

    def embed(self, text: str) -> list[float]:
        if not self.api_key:
            return self._fallback.embed(text)
        try:
            import httpx

            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text[:8000]},
                timeout=30,
            )
            response.raise_for_status()
            vector = response.json()["data"][0]["embedding"]
            if len(vector) != self.dim:
                return self._fallback.embed(text)
            return l2_normalize(vector)
        except Exception:
            return self._fallback.embed(text)


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider.lower() == "openai" and settings.llm_api_key:
        return OpenAIEmbeddingProvider(settings.llm_api_key, settings.embedding_model, settings.embedding_dim)
    return HashingEmbeddingProvider(settings.embedding_dim)
