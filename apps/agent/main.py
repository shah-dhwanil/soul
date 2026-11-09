import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.api.routes import chat, health
from agent.config import get_settings
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.pg.session import create_engine, create_session_factory
from agent.services.memory import MemoryService
from agent.services.turns import TurnService

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with AsyncPostgresSaver.from_conn_string(
        settings.checkpointer_database_url
    ) as checkpointer:
        await checkpointer.setup()
        app.state.turn_service = TurnService(
            settings=settings,
            session_factory=session_factory,
            checkpointer=checkpointer,
            decision_model=DecisionModel(settings),
            query_llm=QueryLLM(settings),
            memory_service=MemoryService(settings),
        )
        app.state.engine = engine
        yield
        await engine.dispose()


app = FastAPI(title="Soul Agent", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(chat.router)
