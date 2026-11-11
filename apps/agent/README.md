# Agent

LangGraph chat agent library: turn graph, Clef decisions, Graphiti memory, and persona prompts.

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

## HTTP API

The FastAPI app lives in the separate [`soul-api`](../api) package (`apps/api`). See [apps/api/README.md](../api/README.md).

Required env: `DATABASE_URL` (e.g. `postgresql+asyncpg://...`), `DATABASE__CHECKPOINTER_DATABASE_URL` (psycopg, for LangGraph), `GROQ_API_KEY`, `GROQ__AGENT_MODEL`, `CF_ACCOUNT_ID`, `CF_AI_API_TOKEN`, plus Graphiti vars for memory retrieval.

Run migrations before first use: `cd apps/agent && uv run alembic upgrade head`.

### Thread split / history injection (Clef)

Clef asks two separate noul questions: **same session** (`thread_continue`, controls DB thread rotation) and **recent context** (`recent_context_required`, controls prompt history). Tune with:

| Setting | Default | Meaning |
| --- | --- | --- |
| `THREAD_INJECT_THRESHOLD` | `0.5` | Inject recent turns when `recent_context_required` ≥ threshold |
| `THREAD_SPLIT_THRESHOLD` | `0.2` | Rotate thread when `thread_continue` (same session) **below** threshold |
| `MEMORY_REQUIRED_THRESHOLD` | `0.35` | Clef `memory_required` yes when score ≥ threshold (logged; retrieval also runs query planner every turn) |
| `MIN_TURNS_BEFORE_SPLIT` | `2` | Ignore split signal until the thread has at least this many stored turns |

Log lines `Clef parse: p_continue=... p_recent=...` help tune thresholds on real chats.

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

Ingestion uses Graphiti **0.31.2**, minimized prompts in [`agent/graphiti/prompts/`](agent/graphiti/prompts/), Groq (`GRAPHITI_LLM_MODEL`, default `openai/gpt-oss-120b`), and Jina `jina-embeddings-v3` at 1024 dimensions against Aura Neo4j (`NEO4J_DATABASE` must match your instance).

Episode text is built with [`build_episode_body`](agent/graphiti/episode.py): user lines only, with selective `Assistant asked:` context for short replies and explicit replies—never a Wren Person node. Pass [`CUSTOM_EXTRACTION_INSTRUCTIONS`](agent/graphiti/episode.py) as `custom_extraction_instructions` on `add_episode`.

```bash
cd apps/agent
uv sync
uv run pytest tests/test_ontology.py -q
```

Required env for workers: `GROQ_API_KEY`, `JINA_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.

### Async memory ingestion (in-process worker)

The memory worker runs inside the **API** process ([`apps/api`](../api)), not this library package alone.

Three Postgres tables:

- **`memory_outbox`** — one durable row per conversation at turn commit (audit).
- **`memory_ingestion_state`** — per-conversation `pending` / `ingested` / `failed` (source of truth for Graphiti backlog).
- **`memory_ingest_job`** — batch jobs: `thread_closed`, `idle_checkpoint`, `user_batch` with worker status (`pending`, `deferred`, …).

On every chat turn (when `memory_ingest_enabled`), the API enqueues `memory_outbox` + `memory_ingestion_state` for that conversation. On Clef **thread split**, a `thread_closed` job is also enqueued on `memory_ingest_job`.

**SLA:** every conversation should reach Graphiti within **`idle_ingest_interval_minutes` (default 30)** of `conversation.finished_at`. `discover_ingest_jobs` runs every **`idle_discover_interval_minutes` (default 5)** and enqueues **`idle_checkpoint`** (priority 1, min batch 1) for any thread with pending state older than the idle threshold. **`user_batch`** (priority 0) runs when a user has **≥ `min_conversations_for_ingest` (10)** pending conversations.

The API polls jobs every ~5s (`outbox_poll_interval_s`) and nudges the worker after `POST /v1/chat` via `BackgroundTasks`. Per-user serialization: only one `processing` job per `user_id` at a time. Set `memory_ingest_enabled=false` to disable worker startup (tests / local chat-only).

Settings (env or defaults): `min_conversations_for_ingest`, `min_conversations_for_idle_flush`, `idle_ingest_interval_minutes`, `idle_discover_interval_minutes`, `outbox_poll_interval_s`, `outbox_max_attempts`, `max_conversations_per_episode`, `memory_ingest_enabled`, `graphiti_build_indices_on_startup`.
