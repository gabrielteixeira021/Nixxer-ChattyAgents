"""Persistence-independent PE4 continuous-memory contract and policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import re
from typing import Protocol, Sequence

from src.backend.core.persona.text import sanitize_prompt_text


SOPHIA_IDENTITY = "sophia"
MAX_ACTIVE_MEMORIES = 1_000
MAX_MEMORY_BYTES = 2_048
MAX_RETRIEVED_MEMORIES = 8
MAX_RETRIEVAL_TOKENS = 1_024
CANDIDATE_RETENTION = timedelta(days=7)
COMPLETED_COMMITMENT_RETENTION = timedelta(days=30)


class MemoryCategory(str, Enum):
    PREFERENCE = "preference"
    PERSONAL_FACT = "personal_fact"
    COMMITMENT = "commitment"


class MemoryOrigin(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    CANDIDATE = "candidate"


class ContinuousMemoryError(Exception):
    """Stable application error safe to translate at adapter boundaries."""

    code = "memory_error"


class MemoryValidationError(ContinuousMemoryError):
    code = "memory_invalid"


class MemoryUnavailableError(ContinuousMemoryError):
    code = "memory_unavailable"


class MemoryCapacityError(ContinuousMemoryError):
    code = "memory_capacity_reached"


class MemoryNotFoundError(ContinuousMemoryError):
    code = "memory_not_found"


class MemoryConflictError(ContinuousMemoryError):
    code = "memory_revision_conflict"


@dataclass(slots=True)
class MemoryRecord:
    id: str
    category: MemoryCategory
    content: str
    fingerprint: str
    origin: MemoryOrigin
    status: MemoryStatus
    source_type: str
    source_timestamp: datetime
    sensitive: bool
    purpose: str | None
    revision: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    completed_at: datetime | None = None


class MemoryStore(Protocol):
    """Port implemented by PE4 persistence adapters."""

    def purge_expired(self, now: datetime) -> None: ...

    def count_active(self) -> int: ...

    def find_duplicate(
        self, category: MemoryCategory, fingerprint: str
    ) -> MemoryRecord | None: ...

    def add(self, record: MemoryRecord) -> None: ...

    def get(self, memory_id: str) -> MemoryRecord | None: ...

    def list_all(self) -> Sequence[MemoryRecord]: ...

    def list_active(self) -> Sequence[MemoryRecord]: ...

    def replace(self, record: MemoryRecord, expected_revision: int) -> None: ...

    def erase(
        self, memory_id: str, expected_revision: int, action: str, now: datetime
    ) -> None: ...

    def audit(self, record: MemoryRecord, action: str, now: datetime) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


_SPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"\w+", re.UNICODE)
_RETRIEVAL_STOPWORDS = frozenset(
    {
        "a",
        "ao",
        "aos",
        "as",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "eu",
        "me",
        "meu",
        "meus",
        "minha",
        "minhas",
        "o",
        "os",
        "qual",
        "quais",
        "que",
        "se",
        "sofia",
        "sophia",
        "um",
        "uma",
        "é",
    }
)
_FORBIDDEN_SECRET = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._~+/=-]{12,}|"
    r"(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|senha)\s*[:=]\s*\S+|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
_FORBIDDEN_SOURCE_TYPES = {"raw_audio", "full_transcript", "model_reply"}


def utc_now() -> datetime:
    """Use naive UTC consistently with this repository's SQLite DateTime fields."""
    return datetime.utcnow()


def normalize_content(content: str) -> str:
    normalized = _SPACE.sub(" ", str(content or "").strip())
    if not normalized:
        raise MemoryValidationError("Memory content must not be empty")
    if len(normalized.encode("utf-8")) > MAX_MEMORY_BYTES:
        raise MemoryValidationError("Memory content exceeds 2,048 UTF-8 bytes")
    if _FORBIDDEN_SECRET.search(normalized):
        raise MemoryValidationError(
            "Credentials and authentication tokens are ineligible"
        )
    return normalized


def validate_source_type(source_type: str) -> str:
    value = _SPACE.sub("_", str(source_type or "").strip().lower())
    if not value or len(value) > 32:
        raise MemoryValidationError("A bounded provenance source_type is required")
    if value in _FORBIDDEN_SOURCE_TYPES:
        raise MemoryValidationError("Raw interaction artifacts are ineligible")
    return value


def validate_purpose(sensitive: bool, purpose: str | None) -> str | None:
    if not sensitive:
        return None
    value = _SPACE.sub(" ", str(purpose or "").strip())
    if not value:
        raise MemoryValidationError(
            "Sensitive memory requires purpose-specific explicit confirmation"
        )
    if len(value) > 160:
        raise MemoryValidationError("Sensitive-memory purpose is too long")
    return value


def fingerprint(content: str) -> str:
    return hashlib.sha256(content.casefold().encode("utf-8")).hexdigest()


def sanitize_retrieval(content: str) -> str:
    """Treat persisted text as data and neutralize prompt-role boundaries."""
    return sanitize_prompt_text(content, ("SophIA",))


def _retrieval_tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.casefold())) - _RETRIEVAL_STOPWORDS


def relevant_records(query: str, records: Sequence[MemoryRecord]) -> list[MemoryRecord]:
    """Deterministic lexical retrieval with record/count/token deduplication caps."""
    clean_query = _SPACE.sub(" ", str(query or "").strip())
    if not clean_query:
        raise MemoryValidationError("Memory retrieval query must not be empty")
    query_tokens = _retrieval_tokens(clean_query)
    if not query_tokens:
        return []

    ranked: list[tuple[int, datetime, str, MemoryRecord]] = []
    for record in records:
        content_tokens = _retrieval_tokens(record.content)
        overlap = len(query_tokens & content_tokens)
        if overlap == 0:
            continue
        phrase_bonus = 2 if clean_query.casefold() in record.content.casefold() else 0
        ranked.append((overlap + phrase_bonus, record.updated_at, record.id, record))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)

    selected: list[MemoryRecord] = []
    seen: set[str] = set()
    used_chars = 0
    max_chars = MAX_RETRIEVAL_TOKENS * 4
    for _, _, _, record in ranked:
        dedup_key = record.content.casefold()
        if dedup_key in seen:
            continue
        clean = sanitize_retrieval(record.content)
        if not clean:
            continue
        if used_chars + len(clean) > max_chars:
            continue
        selected.append(
            MemoryRecord(
                id=record.id,
                category=record.category,
                content=clean,
                fingerprint=record.fingerprint,
                origin=record.origin,
                status=record.status,
                source_type=record.source_type,
                source_timestamp=record.source_timestamp,
                sensitive=record.sensitive,
                purpose=record.purpose,
                revision=record.revision,
                created_at=record.created_at,
                updated_at=record.updated_at,
                expires_at=record.expires_at,
                completed_at=record.completed_at,
            )
        )
        seen.add(dedup_key)
        used_chars += len(clean)
        if len(selected) == MAX_RETRIEVED_MEMORIES:
            break
    return selected
