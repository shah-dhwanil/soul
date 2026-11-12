"""The API's error body shape.

Routes raise the codebase's `HTTPException(status, detail={"code": "..."})`.
On the wire a client sees `{"code": "..."}` — the same shape the auth and
web plans describe — instead of FastAPI's default `{"detail": {...}}`
wrapper. Anything else (FastAPI's own 422 validation body, a 404 for an
unknown path) passes through untouched.
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse


def install_error_handler(app: FastAPI) -> None:
    """Flatten `detail={"code": ...}` errors to a top-level `code` field."""

    @app.exception_handler(HTTPException)
    async def _flatten_code(request: Request, exc: HTTPException) -> Response:
        detail = exc.detail
        if isinstance(detail, dict) and set(detail) == {"code"}:
            return JSONResponse(
                status_code=exc.status_code,
                content=detail,
                headers=exc.headers,
            )
        return await http_exception_handler(request, exc)
