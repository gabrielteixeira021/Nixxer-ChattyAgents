"""Versioned HTTP adapter for the SophIA Persona Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Callable, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.backend.core.config import settings
from src.backend.core.continuous_memory import (
    ContinuousMemoryError,
    ContinuousMemoryService,
    MemoryCapacityError,
    MemoryCategory,
    MemoryConflictError,
    MemoryNotFoundError,
    MemoryOrigin,
    MemoryRecord,
    MemoryStatus,
    MemoryUnavailableError,
    MemoryValidationError,
)
from src.backend.core.persona import (
    ActionFact,
    ActionIntent,
    ActionStatus,
    PersonaContractError,
    PersonaEngine,
)
from src.backend.core.persona.deps import get_persona_engine
from src.backend.db.database import SessionLocal
from src.backend.db.models import Character, User
from src.backend.db.sophia_memory import SqlAlchemyMemoryStore

SERVICE_NAME = "sophia-persona-engine"
API_VERSION = "v1"
NonEmptyString = Annotated[str, Field(min_length=1)]
NonNegativeInteger = Annotated[int, Field(ge=0)]
PositiveInteger = Annotated[int, Field(ge=1)]
MemoryId = Annotated[str, Path(min_length=1, max_length=36)]
T = TypeVar("T")


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


class TurnContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_prompt: Annotated[str, Field(min_length=1, max_length=8192)]


class ActionFactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: ActionIntent
    arguments: Annotated[dict[str, str], Field(min_length=1, max_length=8)]
    status: ActionStatus
    detail: Annotated[str, Field(min_length=1, max_length=512)]


class ActionContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_prompt: Annotated[str, Field(min_length=1, max_length=8192)]
    action: ActionFactRequest


class RememberMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: MemoryCategory
    content: NonEmptyString
    origin: MemoryOrigin
    source_type: Annotated[str, Field(min_length=1, max_length=32)]
    source_timestamp: datetime | None = None
    sensitive: bool = False
    purpose: Annotated[str | None, Field(max_length=160)] = None
    confirmed: bool = False


class MemoryRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    category: MemoryCategory
    content: str
    origin: MemoryOrigin
    status: MemoryStatus
    source_type: str
    source_timestamp: datetime
    sensitive: bool
    purpose: str | None = None
    revision: PositiveInteger
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    completed_at: datetime | None = None


class MemoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memories: list[MemoryRecordResponse]


class RetrieveMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[str, Field(min_length=1, max_length=8192)]


class CorrectMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: NonEmptyString
    expected_revision: PositiveInteger


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: PositiveInteger


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


def _memory_service(db: Session) -> ContinuousMemoryService:
    return ContinuousMemoryService(
        SqlAlchemyMemoryStore(db), enabled=settings.SOPHIA_MEMORY_ENABLED
    )


def _memory_operation(db: Session, operation: Callable[[], T]) -> T:
    try:
        return operation()
    except ContinuousMemoryError as exc:
        db.rollback()
        if isinstance(exc, MemoryNotFoundError):
            status_code = 404
        elif isinstance(exc, (MemoryConflictError, MemoryCapacityError)):
            status_code = 409
        elif isinstance(exc, MemoryValidationError):
            status_code = 422
        elif isinstance(exc, MemoryUnavailableError):
            status_code = 503
        else:
            status_code = 500
        raise _error(status_code, exc.code, str(exc)) from None
    except SQLAlchemyError:
        db.rollback()
        raise _error(
            503,
            "memory_unavailable",
            "Continuous memory persistence is unavailable",
        ) from None


def _memory_response(record: MemoryRecord) -> MemoryRecordResponse:
    return MemoryRecordResponse.model_validate(record)


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


@router.post(
    "/personas/{character_id}/turn-context",
    response_model=PersonaSnapshot,
    operation_id="buildPersonaTurnContext",
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def build_persona_turn_context(
    request: TurnContextRequest,
    character_id: int = Path(ge=1),
    db: Session = Depends(get_persona_db),
    persona_engine: PersonaEngine = Depends(get_persona_service),
) -> PersonaSnapshot:
    """Build prompt context while keeping memory text untrusted and bounded."""
    try:
        character = db.get(Character, character_id)
        if character is None:
            raise _error(
                404,
                "character_not_found",
                f"Character {character_id} was not found",
            )
        memories = _memory_operation(
            db, lambda: _memory_service(db).retrieve(request.user_prompt)
        )
        user = db.query(User).filter(User.is_active.is_(True)).first()
        snapshot = persona_engine.build_snapshot(
            character,
            character.state,
            user,
            memories=(memory.content for memory in memories),
        )
    except PersonaContractError:
        raise _error(
            422,
            "invalid_persona",
            "Stored character cannot satisfy the Persona v1 contract",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _error(
            503,
            "persona_runtime_unavailable",
            "Persona Engine persistence is unavailable",
        ) from None
    return PersonaSnapshot.model_validate(snapshot.as_dict())


@router.post(
    "/personas/{character_id}/action-context",
    response_model=PersonaSnapshot,
    operation_id="buildPersonaActionContext",
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def build_persona_action_context(
    request: ActionContextRequest,
    character_id: int = Path(ge=1),
    db: Session = Depends(get_persona_db),
    persona_engine: PersonaEngine = Depends(get_persona_service),
) -> PersonaSnapshot:
    """Realize authoritative action facts without owning tool execution."""
    try:
        character = db.get(Character, character_id)
        if character is None:
            raise _error(
                404,
                "character_not_found",
                f"Character {character_id} was not found",
            )
        memories = _memory_operation(
            db, lambda: _memory_service(db).retrieve(request.user_prompt)
        )
        user = db.query(User).filter(User.is_active.is_(True)).first()
        action = ActionFact(
            intent=request.action.intent,
            arguments=tuple(request.action.arguments.items()),
            status=request.action.status,
            detail=request.action.detail,
        )
        snapshot = persona_engine.build_action_snapshot(
            character,
            action=action,
            state=character.state,
            user=user,
            memories=(memory.content for memory in memories),
        )
    except PersonaContractError:
        raise _error(
            422,
            "invalid_action_context",
            "Action facts cannot satisfy the Persona v1 contract",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _error(
            503,
            "persona_runtime_unavailable",
            "Persona Engine persistence is unavailable",
        ) from None
    return PersonaSnapshot.model_validate(snapshot.as_dict())


@router.get(
    "/memories",
    response_model=MemoryListResponse,
    operation_id="listSophiaMemories",
    responses={503: {"model": ErrorResponse}},
)
async def list_sophia_memories(
    db: Session = Depends(get_persona_db),
) -> MemoryListResponse:
    records = _memory_operation(db, lambda: _memory_service(db).list_memories())
    return MemoryListResponse(memories=[_memory_response(item) for item in records])


@router.post(
    "/memories",
    response_model=MemoryRecordResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="rememberSophiaMemory",
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def remember_sophia_memory(
    request: RememberMemoryRequest,
    db: Session = Depends(get_persona_db),
) -> MemoryRecordResponse:
    record = _memory_operation(
        db,
        lambda: _memory_service(db).remember(
            category=request.category,
            content=request.content,
            origin=request.origin,
            source_type=request.source_type,
            source_timestamp=request.source_timestamp,
            sensitive=request.sensitive,
            purpose=request.purpose,
            confirmed=request.confirmed,
        ),
    )
    return _memory_response(record)


@router.post(
    "/memories/retrieve",
    response_model=MemoryListResponse,
    operation_id="retrieveSophiaMemories",
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def retrieve_sophia_memories(
    request: RetrieveMemoryRequest,
    db: Session = Depends(get_persona_db),
) -> MemoryListResponse:
    records = _memory_operation(db, lambda: _memory_service(db).retrieve(request.query))
    return MemoryListResponse(memories=[_memory_response(item) for item in records])


@router.patch(
    "/memories/{memory_id}",
    response_model=MemoryRecordResponse,
    operation_id="correctSophiaMemory",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def correct_sophia_memory(
    request: CorrectMemoryRequest,
    memory_id: MemoryId,
    db: Session = Depends(get_persona_db),
) -> MemoryRecordResponse:
    record = _memory_operation(
        db,
        lambda: _memory_service(db).correct(
            memory_id,
            content=request.content,
            expected_revision=request.expected_revision,
        ),
    )
    return _memory_response(record)


@router.delete(
    "/memories/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="forgetSophiaMemory",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def forget_sophia_memory(
    memory_id: MemoryId,
    expected_revision: int = Query(ge=1),
    db: Session = Depends(get_persona_db),
) -> Response:
    _memory_operation(
        db,
        lambda: _memory_service(db).forget(
            memory_id, expected_revision=expected_revision
        ),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/memories/{memory_id}/confirm",
    response_model=MemoryRecordResponse,
    operation_id="confirmSophiaMemory",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def confirm_sophia_memory(
    request: RevisionRequest,
    memory_id: MemoryId,
    db: Session = Depends(get_persona_db),
) -> MemoryRecordResponse:
    record = _memory_operation(
        db,
        lambda: _memory_service(db).confirm(
            memory_id, expected_revision=request.expected_revision
        ),
    )
    return _memory_response(record)


@router.post(
    "/memories/{memory_id}/complete",
    response_model=MemoryRecordResponse,
    operation_id="completeSophiaCommitment",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def complete_sophia_commitment(
    request: RevisionRequest,
    memory_id: MemoryId,
    db: Session = Depends(get_persona_db),
) -> MemoryRecordResponse:
    record = _memory_operation(
        db,
        lambda: _memory_service(db).complete(
            memory_id, expected_revision=request.expected_revision
        ),
    )
    return _memory_response(record)
