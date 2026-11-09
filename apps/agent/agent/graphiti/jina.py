"""Jina embeddings adapter for Graphiti."""

import asyncio
import os
from collections.abc import Iterable

import httpx
from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig


class JinaEmbedderConfig(EmbedderConfig):
    api_key: str
    model: str = "jina-embeddings-v3"
    task: str = "retrieval.passage"


class JinaEmbedder(EmbedderClient):
    def __init__(self, config: JinaEmbedderConfig | None = None) -> None:
        if config is None:
            api_key = os.environ.get("JINA_API_KEY")
            if not api_key:
                raise ValueError("JINA_API_KEY is required for JinaEmbedder")
            config = JinaEmbedderConfig(api_key=api_key)
        self.config = config
        self._client = httpx.AsyncClient(
            base_url="https://api.jina.ai/v1",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post(
                    "/embeddings",
                    json={
                        "model": self.config.model,
                        "input": texts,
                        "dimensions": self.config.embedding_dim,
                        "task": self.config.task,
                    },
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                response.raise_for_status()
                payload = response.json()
                vectors = [item["embedding"] for item in payload["data"]]
                for vector in vectors:
                    if len(vector) != self.config.embedding_dim:
                        raise ValueError(
                            f"expected dim {self.config.embedding_dim}, got {len(vector)}"
                        )
                return vectors
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
        raise RuntimeError("Jina embedding request failed") from last_error

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float]:
        if isinstance(input_data, str):
            texts = [input_data]
        elif isinstance(input_data, list) and all(isinstance(x, str) for x in input_data):
            texts = input_data
        else:
            raise TypeError("JinaEmbedder only supports string input")
        vectors = await self._embed_texts(texts)
        return vectors[0]

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        return await self._embed_texts(input_data_list)

    async def aclose(self) -> None:
        await self._client.aclose()
