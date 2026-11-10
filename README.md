# soul

Wren conversational companion — Python workspace (`uv`) with the LangGraph **agent** library in `apps/agent`, the **HTTP API** in `apps/api`, and minimized Graphiti ingestion prompts under `apps/agent/agent/graphiti/prompts/`.

```bash
uv sync
cd apps/agent
uv run pytest tests/test_ontology.py -q
cd ../api
uv run uvicorn main:app --reload
```
