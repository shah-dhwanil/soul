from fastapi import FastAPI

from agent.api.routes import chat, health


def create_app() -> FastAPI:
    app = FastAPI(title="Soul Agent", version="0.1.0")
    app.include_router(health.router)
    app.include_router(chat.router)
    return app
