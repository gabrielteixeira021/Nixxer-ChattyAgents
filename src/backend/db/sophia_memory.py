"""SQLAlchemy adapter for the PE4 continuous-memory port."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.backend.core.continuous_memory.domain import (
    SOPHIA_IDENTITY,
    MemoryCategory,
    MemoryConflictError,
    MemoryOrigin,
    MemoryRecord,
    MemoryStatus,
)
from src.backend.db.models import SophiaMemory, SophiaMemoryAudit


class SqlAlchemyMemoryStore:
    def __init__(self, db: Session) -> None:
        self._db = db

    def purge_expired(self, now: datetime) -> None:
        expired = (
            self._db.query(SophiaMemory)
            .filter(
                SophiaMemory.identity_key == SOPHIA_IDENTITY,
                SophiaMemory.expires_at.is_not(None),
                SophiaMemory.expires_at <= now,
            )
            .all()
        )
        for model in expired:
            self._db.add(
                SophiaMemoryAudit(
                    memory_id=model.id,
                    action="expired",
                    revision=model.revision,
                    occurred_at=now,
                )
            )
            self._db.delete(model)

    def count_active(self) -> int:
        return (
            self._db.query(SophiaMemory)
            .filter(
                SophiaMemory.identity_key == SOPHIA_IDENTITY,
                SophiaMemory.status == MemoryStatus.ACTIVE.value,
            )
            .count()
        )

    def find_duplicate(
        self, category: MemoryCategory, fingerprint: str
    ) -> MemoryRecord | None:
        model = (
            self._db.query(SophiaMemory)
            .filter(
                SophiaMemory.identity_key == SOPHIA_IDENTITY,
                SophiaMemory.category == category.value,
                SophiaMemory.content_fingerprint == fingerprint,
            )
            .first()
        )
        return self._record(model)

    def add(self, record: MemoryRecord) -> None:
        self._db.add(self._model(record))

    def get(self, memory_id: str) -> MemoryRecord | None:
        model = (
            self._db.query(SophiaMemory)
            .filter(
                SophiaMemory.id == memory_id,
                SophiaMemory.identity_key == SOPHIA_IDENTITY,
            )
            .first()
        )
        return self._record(model)

    def list_all(self) -> Sequence[MemoryRecord]:
        rows = (
            self._db.query(SophiaMemory)
            .filter(SophiaMemory.identity_key == SOPHIA_IDENTITY)
            .order_by(SophiaMemory.updated_at.desc(), SophiaMemory.id.desc())
            .all()
        )
        return [self._record(row) for row in rows]

    def list_active(self) -> Sequence[MemoryRecord]:
        rows = (
            self._db.query(SophiaMemory)
            .filter(
                SophiaMemory.identity_key == SOPHIA_IDENTITY,
                SophiaMemory.status == MemoryStatus.ACTIVE.value,
            )
            .all()
        )
        return [self._record(row) for row in rows]

    def replace(self, record: MemoryRecord, expected_revision: int) -> None:
        values = self._values(record)
        try:
            result = self._db.execute(
                update(SophiaMemory)
                .where(
                    SophiaMemory.id == record.id,
                    SophiaMemory.identity_key == SOPHIA_IDENTITY,
                    SophiaMemory.revision == expected_revision,
                )
                .values(**values)
            )
        except IntegrityError:
            self._db.rollback()
            raise MemoryConflictError(
                "An equivalent memory already exists in this category"
            ) from None
        if result.rowcount != 1:
            raise MemoryConflictError("Memory revision changed concurrently")

    def erase(
        self, memory_id: str, expected_revision: int, action: str, now: datetime
    ) -> None:
        result = self._db.execute(
            delete(SophiaMemory).where(
                SophiaMemory.id == memory_id,
                SophiaMemory.identity_key == SOPHIA_IDENTITY,
                SophiaMemory.revision == expected_revision,
            )
        )
        if result.rowcount != 1:
            raise MemoryConflictError("Memory revision changed concurrently")
        self._db.add(
            SophiaMemoryAudit(
                memory_id=memory_id,
                action=action,
                revision=expected_revision,
                occurred_at=now,
            )
        )

    def audit(self, record: MemoryRecord, action: str, now: datetime) -> None:
        self._db.add(
            SophiaMemoryAudit(
                memory_id=record.id,
                action=action,
                revision=record.revision,
                occurred_at=now,
            )
        )

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    @staticmethod
    def _record(model: SophiaMemory | None) -> MemoryRecord | None:
        if model is None:
            return None
        return MemoryRecord(
            id=model.id,
            category=MemoryCategory(model.category),
            content=model.content,
            fingerprint=model.content_fingerprint,
            origin=MemoryOrigin(model.origin),
            status=MemoryStatus(model.status),
            source_type=model.source_type,
            source_timestamp=model.source_timestamp,
            sensitive=model.sensitive,
            purpose=model.purpose,
            revision=model.revision,
            created_at=model.created_at,
            updated_at=model.updated_at,
            expires_at=model.expires_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def _values(record: MemoryRecord) -> dict:
        return {
            "category": record.category.value,
            "content": record.content,
            "content_fingerprint": record.fingerprint,
            "origin": record.origin.value,
            "status": record.status.value,
            "source_type": record.source_type,
            "source_timestamp": record.source_timestamp,
            "sensitive": record.sensitive,
            "purpose": record.purpose,
            "revision": record.revision,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "expires_at": record.expires_at,
            "completed_at": record.completed_at,
        }

    @classmethod
    def _model(cls, record: MemoryRecord) -> SophiaMemory:
        return SophiaMemory(
            id=record.id,
            identity_key=SOPHIA_IDENTITY,
            **cls._values(record),
        )
