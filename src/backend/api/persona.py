"""Versioned HTTP adapter for the SophIA Persona Engine."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.backend.core.persona import PersonaContractError, PersonaEngine
from src.backend.core.persona.deps import get_persona_engine
from src.backend.db.database import SessionLocal
from src.backend.db.models import Character, User

SERVICE_NAME = "sophia-persona-engine"
API_VERSION = "v1"
NonEmptyString = Annotated[str, Field(min_length=1)]
NonNegativeInteger = Annotated[int, Field(ge=0)]


class HealthComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_engine: Literal["ready"]
    database: Literal["ready"]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"]
    service: Literal["sophia-persona-engine"]
    api_version: Literal["v1"]
    persona_schema_version: Literal[1]
    components: HealthComponents


class PersonaSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    character_name: NonEmptyString
    system_prompt: NonEmptyString
    mood: NonEmptyString
    dynamic: bool
    revision: NonNegativeInteger


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: ErrorDetail


router = APIRouter(tags=["Persona"])


async def get_persona_db():
    """Own one synchronous SQLite session for a short local API request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_persona_service() -> PersonaEngine:
    """Expose the domain singleton without a framework dependency in core."""
    return get_persona_engine()


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    operation_id="getPersonaHealth",
    responses={503: {"model": ErrorResponse}},
)
async def get_persona_health(
    db: Session = Depends(get_persona_db),
    persona_engine: PersonaEngine = Depends(get_persona_service),
) -> HealthResponse:
    """Report readiness only after the domain service and database respond."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise _error(
            503,
            "persona_runtime_unavailable",
            "Persona Engine persistence is unavailable",
        ) from None

    return HealthResponse(
        status="ready",
        service=SERVICE_NAME,
        api_version=API_VERSION,
        persona_schema_version=persona_engine.SCHEMA_VERSION,
        components=HealthComponents(persona_engine="ready", database="ready"),
    )


@router.get(
    "/personas/{character_id}/snapshot",
    response_model=PersonaSnapshot,
    operation_id="getPersonaSnapshot",
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def get_persona_snapshot(
    character_id: int = Path(ge=1),
    db: Session = Depends(get_persona_db),
    persona_engine: PersonaEngine = Depends(get_persona_service),
) -> PersonaSnapshot:
    """Build a read-only snapshot from the current persisted character state."""
    try:
        character = db.get(Character, character_id)
        if character is None:
            raise _error(
                404,
                "character_not_found",
                f"Character {character_id} was not found",
            )

        user = db.query(User).filter(User.is_active.is_(True)).first()
        snapshot = persona_engine.build_snapshot(character, character.state, user)
    except PersonaContractError:
        raise _error(
            422,
            "invalid_persona",
            "Stored character cannot satisfy the Persona v1 contract",
        ) from None
    except SQLAlchemyError:
        raise _error(
            503,
            "persona_runtime_unavailable",
            "Persona Engine persistence is unavailable",
        ) from None

    return PersonaSnapshot.model_validate(snapshot.as_dict())
