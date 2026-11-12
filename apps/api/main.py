import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.config import get_settings
from agent.logging_config import configure_logging
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.pg.session import create_engine, create_session_factory
from agent.services.detection import DetectionWorker
from agent.services.ingest import IngestService
from agent.services.memory import MemoryService
from agent.services.memory_worker import MemoryWorker
from agent.services.recompute import RecomputeWorker
from agent.services.turns import TurnService
from api.config import get_auth_settings
from api.routes import chat, health, users

_api_root = Path(__file__).resolve().parent
load_dotenv(_api_root / ".env")
load_dotenv(_api_root.parent / "agent" / ".env")
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Fail fast: without JWT_SECRET the API cannot validate an access token,
    # and serving identity it cannot verify is worse than not serving at all.
    get_auth_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with AsyncPostgresSaver.from_conn_string(
        settings.checkpointer_database_url
    ) as checkpointer:
        await checkpointer.setup()
        memory_service = MemoryService(settings)
        app.state.session_factory = session_factory
        app.state.memory_service = memory_service
        app.state.turn_service = TurnService(
            settings=settings,
            session_factory=session_factory,
            checkpointer=checkpointer,
            decision_model=DecisionModel(settings),
            query_llm=QueryLLM(settings),
            memory_service=memory_service,
        )
        ingest_service = IngestService(settings)
        memory_worker = MemoryWorker(
            settings=settings,
            session_factory=session_factory,
            ingest_service=ingest_service,
        )
        await memory_worker.start()
        app.state.memory_worker = memory_worker
        detection_worker = DetectionWorker(
            settings=settings, session_factory=session_factory
        )
        await detection_worker.start()
        app.state.detection_worker = detection_worker
        recompute_worker = RecomputeWorker(
            settings=settings, session_factory=session_factory
        )
        await recompute_worker.start()
        app.state.recompute_worker = recompute_worker
        app.state.engine = engine
        yield
        await recompute_worker.stop()
        await detection_worker.stop()
        await memory_worker.stop()
        await engine.dispose()


app = FastAPI(title="Soul API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(users.router)
