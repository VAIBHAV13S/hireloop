# Embedder Interface and Implementations for HireLoop

import abc
import hashlib
import math
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024

class BaseEmbedder(abc.ABC):
    """Abstract base embedder interface."""

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        pass

    @abc.abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string into a normalized float vector."""
        pass

    @abc.abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings into normalized float vectors."""
        pass

class GeminiEmbedder(BaseEmbedder):
    """Google Gemini neural embedder using text-embedding-004 via Google AI Studio API."""

    def __init__(self, api_key: str, model: str = "text-embedding-004", dim: int = EMBEDDING_DIM):
        self._api_key = api_key
        self._model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return f"gemini-{self._model}"

    async def embed_text(self, text: str) -> List[float]:
        batch = await self.embed_batch([text])
        return batch[0] if batch else [0.0] * self._dim

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        import httpx

        # text-embedding-004 batch endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:batchEmbedContents?key={self._api_key}"
        requests_payload = [
            {
                "model": f"models/{self._model}",
                "content": {"parts": [{"text": t[:2048]}]}
            }
            for t in texts
        ]

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json={"requests": requests_payload})
                if resp.status_code == 200:
                    data = resp.json()
                    raw_embeddings = data.get("embeddings", [])
                    results = []
                    for item in raw_embeddings:
                        vec = item.get("values", [])
                        # Pad or truncate to self._dim (1024) to match PostgreSQL schema Vector(1024)
                        if len(vec) < self._dim:
                            vec = vec + [0.0] * (self._dim - len(vec))
                        elif len(vec) > self._dim:
                            vec = vec[:self._dim]

                        # Unit normalize vector for cosine / dot product similarity
                        norm = math.sqrt(sum(x * x for x in vec))
                        if norm > 0.0:
                            vec = [x / norm for x in vec]
                        results.append(vec)
                    return results
                else:
                    logger.warning(
                        f"Gemini embedding API returned status {resp.status_code}: {resp.text[:200]}. Falling back to deterministic embedder."
                    )
        except Exception as e:
            logger.warning(f"Gemini embedder failed ({e}), falling back to deterministic local embedder.")

        fallback = DeterministicLocalEmbedder(dim=self._dim)
        return [await fallback.embed_text(t) for t in texts]


class HostedAPIEmbedder(BaseEmbedder):
    """Hosted Embedding API (OpenAI text-embedding-3-small or custom endpoint)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dim: int = EMBEDDING_DIM):
        self._api_key = api_key
        self._model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model

    async def embed_text(self, text: str) -> List[float]:
        batch = await self.embed_batch([text])
        return batch[0] if batch else [0.0] * self._dim

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._api_key)
            response = await client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dim,
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.warning(f"Hosted embedder failed ({e}), falling back to deterministic local embedder.")
            fallback = DeterministicLocalEmbedder(dim=self._dim)
            return [await fallback.embed_text(t) for t in texts]

class DeterministicLocalEmbedder(BaseEmbedder):
    """Offline deterministic semantic pseudo-embedder.

    Produces consistent 1024-dim unit-normalized vectors via token hashing and
    bag-of-words projection, allowing offline local dev, testing, and CI
    without external API keys or expensive GPU dependencies.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "hireloop-deterministic-v1"

    def embed_text_sync(self, text: str) -> List[float]:
        tokens = [t.lower().strip() for t in text.split() if t.strip()]
        if not tokens:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    async def embed_text(self, text: str) -> List[float]:
        return self.embed_text_sync(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]

_active_embedder: Optional[BaseEmbedder] = None

def get_embedder() -> BaseEmbedder:
    """Return the configured embedder instance (singleton)."""
    global _active_embedder
    if _active_embedder is None:
        gemini_key = ""
        openai_key = ""
        try:
            from hireloop.apps.api.app.core.settings import settings
            gemini_key = getattr(settings, "GEMINI_API_KEY", "")
            openai_key = getattr(settings, "OPENAI_API_KEY", "")
        except Exception:
            pass

        if gemini_key:
            _active_embedder = GeminiEmbedder(api_key=gemini_key)
        elif openai_key:
            _active_embedder = HostedAPIEmbedder(api_key=openai_key)
        else:
            _active_embedder = DeterministicLocalEmbedder()
    return _active_embedder
