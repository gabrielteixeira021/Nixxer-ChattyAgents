"""Minimal loopback service for the SophIA Persona Engine API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.backend.api.persona import router as persona_router
from src.backend.core.config import settings
from src.backend.db.database import init_db

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize only persistence; PE2 deliberately boots no LLM runtime."""
    if not settings.TESTING:
        init_db()
    yield


app = FastAPI(
    title="SophIA Persona Engine API",
    version="1.0.0",
    description="Loopback-only persona snapshot service for SophIA.",
    lifespan=lifespan,
)
app.include_router(persona_router, prefix="/v1")


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    """Keep validation failures inside the stable Persona error envelope."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "request_validation_error",
                "message": "Request does not satisfy the Persona v1 contract",
            }
        },
    )


def run(port: int = DEFAULT_PORT) -> None:
    """Run the dedicated service on the loopback-only MVP boundary."""
    import uvicorn

    uvicorn.run(app, host=DEFAULT_HOST, port=port)


if __name__ == "__main__":
    run()
