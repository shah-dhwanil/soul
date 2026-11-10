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
GROQ__AGENT_MODEL=openai/gpt-oss-120b
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

Required env: `DATABASE_URL` (e.g. `postgresql+asyncpg://...`), `DATABASE__CHECKPOINTER_DATABASE_URL` (psycopg, for LangGraph), `GROQ_API_KEY`, `GROQ__AGENT_MODEL`, `CF_ACCOUNT_ID`, `CF_AI_API_TOKEN`, plus Graphiti vars for memory retrieval.

Run migrations before first use: `cd apps/agent && uv run alembic upgrade head`.

## End-to-end eval (synthetic + LLM judge)

Synthetic scenarios live in [`agent/evals/scenarios.py`](agent/evals/scenarios.py). Each turn is run through the real turn pipeline, then scored by a Groq judge plus deterministic checks (banned phrases, question budget).

```bash
cd apps/agent
uv run python scripts/run_agent_eval.py
uv run python scripts/run_agent_eval.py --scenario gujarati_casual_greeting --fail-fast
```

Offline unit tests (no live APIs): `uv run pytest tests/evals -q`

Live full suite (costs Clef + Groq + DB): `uv run pytest tests/evals -m eval -q` when `test_agent_eval_live.py` is present and creds are set.

## Graphiti memory ingestion

Ingestion uses Graphiti **0.31.2**, minimized prompts in [`graphiti_prompts/`](../../graphiti_prompts/), Groq (`GRAPHITI_LLM_MODEL`, default `openai/gpt-oss-120b`), and Jina `jina-embeddings-v3` at 1024 dimensions against Aura Neo4j (`NEO4J_DATABASE` must match your instance).

Episode text is built with [`build_episode_body`](agent/graphiti/episode.py): user lines only, with selective `Assistant asked:` context for short replies and explicit replies—never a Wren Person node. Pass [`CUSTOM_EXTRACTION_INSTRUCTIONS`](agent/graphiti/episode.py) as `custom_extraction_instructions` on `add_episode`.

```bash
cd apps/agent
uv sync
uv run pytest tests/test_ontology.py -q
```

Required env for workers: `GROQ_API_KEY`, `JINA_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.

### Async memory outbox (in-process worker)

- On Clef **thread split**, a `thread_closed` row is enqueued in `agent.memory_outbox` (same transaction as the new conversation).
- **Graphiti ingest** runs only when a batch has at least **10** un-ingested conversations (`min_conversations_for_ingest`); smaller completed threads are marked `deferred` until a **30m** scheduler enqueues a `user_batch` for that user.
- The API process polls the outbox every ~5s and nudges the worker after `POST /v1/chat` via `BackgroundTasks`.
- Per-user serialization: only one `processing` job per `user_id` at a time.
- Set `memory_ingest_enabled=false` to disable worker startup (tests / local chat-only).

Settings (env or defaults): `min_conversations_for_ingest`, `idle_ingest_interval_minutes`, `outbox_poll_interval_s`, `outbox_max_attempts`, `max_conversations_per_episode`, `memory_ingest_enabled`, `graphiti_build_indices_on_startup`.
