# Agent

LangGraph chat agent backed by Groq.

## Gradio test UI

From the repo root:

```bash
uv sync
cd apps/agent
uv run python gradio_app.py
```

Ensure `apps/agent/.env` defines nested Groq settings (see [pydantic-settings nested env](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values)):

```env
GROQ__API_KEY=...
GROQ__AGENT_MODEL=...
DATABASE__CHECKPOINTER_DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
```

LangGraph checkpoint tables use **psycopg** (`postgresql://…`), not asyncpg. On first run the app calls `AsyncPostgresSaver.setup()` to create migration tables. Canonical chat history for production should still live in your app database; checkpoints are for graph durability and replay.

Alternatively:

```bash
cd apps/agent
uv run python main.py
```

## HTTP API

```bash
cd apps/agent
uv run uvicorn main:app --reload
```

`POST /v1/chat` with `{"user_id": "...", "message": "..."}` runs the LangGraph turn pipeline (Clef decisions, optional Graphiti retrieval, Groq reply). Each graph invoke uses a new LangGraph `thread_id` (`turn_id`); Postgres `thread` rows group conversations until Clef signals a split.

Required env: `DATABASE_URL` (asyncpg), `DATABASE__CHECKPOINTER_DATABASE_URL` (psycopg), `GROQ_API_KEY`, `GROQ__AGENT_MODEL`, `CF_ACCOUNT_ID`, `CF_AI_API_TOKEN`, plus Graphiti vars for memory retrieval.

## Graphiti memory ingestion

Ingestion uses Graphiti **0.31.2**, minimized prompts in [`graphiti_prompts/`](../../graphiti_prompts/), Groq (`GRAPHITI_LLM_MODEL`, default `openai/gpt-oss-120b`), and Jina `jina-embeddings-v3` at 1024 dimensions against Aura Neo4j (`NEO4J_DATABASE` must match your instance).

Episode text is built with [`build_episode_body`](agent/graphiti/episode.py): user lines only, with selective `Assistant asked:` context for short replies and explicit replies—never a Wren Person node. Pass [`CUSTOM_EXTRACTION_INSTRUCTIONS`](agent/graphiti/episode.py) as `custom_extraction_instructions` on `add_episode`.

```bash
cd apps/agent
uv sync
uv run pytest tests/test_ontology.py -q
```

Required env for workers: `GROQ_API_KEY`, `JINA_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.
