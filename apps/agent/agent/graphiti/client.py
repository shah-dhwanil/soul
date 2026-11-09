"""Construct a configured Graphiti client for ingestion workers."""

import os

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.llm_client import LLMRuntime, LLMTransport
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.groq_client import GroqClient

from agent.graphiti.jina import JinaEmbedder, JinaEmbedderConfig
from agent.graphiti.prompt_overrides import build_prompt_overrides


class _PassThroughCrossEncoder(CrossEncoderClient):
    """Avoid the default OpenAI reranker until a production reranker is wired."""

    async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]:
        del query
        return [(passage, float(len(passages) - index)) for index, passage in enumerate(passages)]


DEFAULT_GRAPHITI_LLM_MODEL = "openai/gpt-oss-120b"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


async def create_graphiti(*, build_indices: bool = True) -> Graphiti:
    """Build Graphiti with Groq LLM, Jina embeddings, and minimized prompts."""
    groq_key = _require_env("GROQ_API_KEY")
    llm_model = os.environ.get("GRAPHITI_LLM_MODEL", DEFAULT_GRAPHITI_LLM_MODEL)
    llm_client = GroqClient(LLMConfig(api_key=groq_key, model=llm_model))

    jina_key = _require_env("JINA_API_KEY")
    embedder = JinaEmbedder(JinaEmbedderConfig(api_key=jina_key))

    uri = _require_env("NEO4J_URI")
    user = _require_env("NEO4J_USERNAME")
    password = _require_env("NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    driver = Neo4jDriver(uri=uri, user=user, password=password, database=database)
    runtime = LLMRuntime(
        model=LLMTransport(llm_client).model(llm_model),
        prompt_overrides=build_prompt_overrides(),
    )
    llm_kwargs = {"llm_runtime": runtime}

    graphiti = Graphiti(
        graph_driver=driver,
        embedder=embedder,
        cross_encoder=_PassThroughCrossEncoder(),
        max_coroutines=2,
        **llm_kwargs,
    )
    if build_indices:
        await graphiti.build_indices_and_constraints()
    return graphiti
