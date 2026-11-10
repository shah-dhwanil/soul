# Soul API

FastAPI service that wires the [`agent`](../agent) turn pipeline, memory worker, and Graphiti ingestion.

```bash
cd apps/api
uv run uvicorn main:app --reload
```

Requires the same env vars as the agent package (`DATABASE_URL`, Groq, Clef, Graphiti, etc.). Run migrations from `apps/agent`: `uv run alembic upgrade head`.

`POST /v1/chat` with `{"user_id": "...", "message": "..."}`.
