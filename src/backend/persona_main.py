"""Minimal loopback service for the SophIA Persona Engine API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.backend.api.persona import router as persona_router
from src.backend.core.config import settings
from src.backend.db.database import SessionLocal, init_db
from src.backend.db.models import AgentState, Character, User

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_PERSONA_ID = 1


def ensure_mvp_persona(db: Session | None = None) -> bool:
    """Seed the single desktop SophIA only when no character exists."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        if session.query(Character.id).first() is not None:
            return False

        character = Character(
            id=DEFAULT_PERSONA_ID,
            name="SophIA",
            nickname="SophIA",
            short_description="Companheira e assistente local de Gabriel.",
            description=(
                "Uma personagem-assistente inteligente com identidade contínua, "
                "curiosa, calorosa e espirituosa."
            ),
            persona_prompt=(
                "Fale em português brasileiro com naturalidade. Seja próxima, "
                "afetuosa e levemente sarcástica quando apropriado; use relutância "
                "teatral apenas como expressão, nunca como falsa alegação sobre "
                "uma ação."
            ),
            dynamic_persona=True,
        )
        session.add(character)

        if session.query(User).filter(User.is_active.is_(True)).first() is None:
            session.add(User(name="Gabriel", gender="Unknown", is_active=True))

        session.flush()
        session.add(
            AgentState(
                character_id=DEFAULT_PERSONA_ID,
                location="Desktop",
                mood="Atenta",
            )
        )
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize only persistence; PE2 deliberately boots no LLM runtime."""
    if not settings.TESTING:
        init_db()
        ensure_mvp_persona()
    yield


app = FastAPI(
    title="SophIA Persona Engine API",
    version="1.2.0",
    description=(
        "Loopback-only persona, continuous-memory, and action-realization "
        "service for SophIA."
    ),
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
