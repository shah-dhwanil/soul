# soul

Wren conversational companion — Python workspace (`uv`) with the LangGraph **agent** library in `apps/agent`, the **HTTP API** in `apps/api`, and minimized Graphiti ingestion prompts under `apps/agent/agent/graphiti/prompts/`.

## Character system

Wren's voice is built from a hashed persona prompt, fixed product constants (modes, dial floors, temperament seeds, banned phrases, boundary scripts, crisis resources), and per-user state in Postgres (stage, traits, leanings, dependency level). Each turn, Clef classifies the concern tier, register, and situation, and a per-turn directive budgets mode, length, questions, and humour. Vocabulary is in [CONTEXT.md](CONTEXT.md); design decisions are in [docs/adr](docs/adr); pre-release checks are in [docs/persona-release-checklist.md](docs/persona-release-checklist.md).

- Spec: [Wren Companion Persona Spec v2.2](docs/Wren%20Companion%20Persona%20Spec%20v2.2.md)
- Plan: [docs/superpowers/plans/2026-11-12-wren-character-system.md](docs/superpowers/plans/2026-11-12-wren-character-system.md)

## Development

```bash
uv sync
cd apps/agent
uv run pytest tests/unit tests/evals -q -m "not integration and not eval"
uv run ruff check .
uv run mypy agent
cd ../api
uv run pytest tests -q
uv run uvicorn main:app --reload
```

Live evals (costs credits, pre-release): see [apps/agent/README.md](apps/agent/README.md#persona-layer).
