import asyncio
import logging
from typing import Any

from agent.config import Settings

logger = logging.getLogger(__name__)
from agent.graphiti.client import create_graphiti


class MemoryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, user_id: str, queries: list[str]) -> tuple[list[dict[str, Any]], bool]:
        if not queries:
            return [], False
        degraded = False
        all_facts: list[dict[str, Any]] = []
        seen: set[str] = set()
        graphiti = None
        try:
            graphiti = await create_graphiti(build_indices=False)
            timeout = self._settings.memory_search_timeout_seconds

            async def run_query(query: str) -> list[dict[str, Any]]:
                edges = await graphiti.search(
                    query,
                    group_ids=[user_id],
                    num_results=self._settings.memory_num_results,
                )
                return [{"fact": edge.fact, "query": query} for edge in edges]

            tasks = [run_query(q) for q in queries]
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks),
                    timeout=timeout,
                )
            except TimeoutError:
                degraded = True
                results = []

            for batch in results:
                for item in batch:
                    fact = item["fact"]
                    if fact not in seen:
                        seen.add(fact)
                        all_facts.append(item)
        except Exception:
            logger.exception("Graphiti memory search failed for user=%s", user_id)
            degraded = True
        finally:
            if graphiti is not None:
                await graphiti.close()
        if degraded:
            logger.warning(
                "Memory degraded user=%s queries=%s facts=%d",
                user_id,
                queries,
                len(all_facts),
            )
        else:
            logger.info(
                "Memory search user=%s queries=%d facts=%d",
                user_id,
                len(queries),
                len(all_facts),
            )
        return all_facts, degraded
