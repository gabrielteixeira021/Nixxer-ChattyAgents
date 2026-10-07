"""PE4 use cases over the continuous-memory persistence port."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from src.backend.core.continuous_memory.domain import (
    CANDIDATE_RETENTION,
    COMPLETED_COMMITMENT_RETENTION,
    MAX_ACTIVE_MEMORIES,
    MemoryCapacityError,
    MemoryCategory,
    MemoryConflictError,
    MemoryNotFoundError,
    MemoryOrigin,
    MemoryRecord,
    MemoryStatus,
    MemoryStore,
    MemoryUnavailableError,
    MemoryValidationError,
    fingerprint,
    normalize_content,
    relevant_records,
    utc_now,
    validate_purpose,
    validate_source_type,
)


class ContinuousMemoryService:
    def __init__(
        self,
        store: MemoryStore,
        *,
        enabled: bool = True,
        clock=utc_now,
    ) -> None:
        self._store = store
        self._enabled = enabled
        self._clock = clock

    def remember(
        self,
        *,
        category: MemoryCategory,
        content: str,
        origin: MemoryOrigin,
        source_type: str,
        source_timestamp: datetime | None = None,
        sensitive: bool = False,
        purpose: str | None = None,
        confirmed: bool = False,
    ) -> MemoryRecord:
        self._require_enabled()
        now = self._clock()
        self._store.purge_expired(now)
        normalized = normalize_content(content)
        source = validate_source_type(source_type)
        if sensitive and (origin is not MemoryOrigin.EXPLICIT or not confirmed):
            raise MemoryValidationError(
                "Sensitive memory requires an explicit user confirmation"
            )
        clean_purpose = validate_purpose(sensitive, purpose)
        status = (
            MemoryStatus.ACTIVE
            if origin is MemoryOrigin.EXPLICIT or confirmed
            else MemoryStatus.CANDIDATE
        )
        digest = fingerprint(normalized)
        duplicate = self._store.find_duplicate(category, digest)
        if duplicate is not None:
            if (
                duplicate.status is MemoryStatus.CANDIDATE
                and status is MemoryStatus.ACTIVE
            ):
                self._require_capacity()
            refreshed = replace(
                duplicate,
                origin=origin,
                status=status,
                source_type=source,
                source_timestamp=source_timestamp or now,
                sensitive=sensitive,
                purpose=clean_purpose,
                revision=duplicate.revision + 1,
                updated_at=now,
                expires_at=now + CANDIDATE_RETENTION
                if status is MemoryStatus.CANDIDATE
                else None,
            )
            self._store.replace(refreshed, duplicate.revision)
            self._store.audit(refreshed, "refreshed", now)
            self._store.commit()
            return refreshed

        if status is MemoryStatus.ACTIVE:
            self._require_capacity()

        record = MemoryRecord(
            id=str(uuid4()),
            category=category,
            content=normalized,
            fingerprint=digest,
            origin=origin,
            status=status,
            source_type=source,
            source_timestamp=source_timestamp or now,
            sensitive=sensitive,
            purpose=clean_purpose,
            revision=1,
            created_at=now,
            updated_at=now,
            expires_at=now + CANDIDATE_RETENTION
            if status is MemoryStatus.CANDIDATE
            else None,
        )
        self._store.add(record)
        self._store.audit(record, "created", now)
        self._store.commit()
        return record

    def list_memories(self) -> list[MemoryRecord]:
        self._require_enabled()
        self._store.purge_expired(self._clock())
        self._store.commit()
        return list(self._store.list_all())

    def retrieve(self, query: str) -> list[MemoryRecord]:
        self._require_enabled()
        now = self._clock()
        self._store.purge_expired(now)
        self._store.commit()
        return relevant_records(query, self._store.list_active())

    def correct(
        self,
        memory_id: str,
        *,
        content: str,
        expected_revision: int,
    ) -> MemoryRecord:
        self._require_enabled()
        record = self._required(memory_id)
        self._check_revision(record, expected_revision)
        normalized = normalize_content(content)
        updated = replace(
            record,
            content=normalized,
            fingerprint=fingerprint(normalized),
            revision=record.revision + 1,
            updated_at=self._clock(),
        )
        self._store.replace(updated, expected_revision)
        self._store.audit(updated, "corrected", updated.updated_at)
        self._store.commit()
        return updated

    def confirm(self, memory_id: str, *, expected_revision: int) -> MemoryRecord:
        self._require_enabled()
        record = self._required(memory_id)
        self._check_revision(record, expected_revision)
        if record.status is MemoryStatus.ACTIVE:
            return record
        self._require_capacity()
        updated = replace(
            record,
            status=MemoryStatus.ACTIVE,
            revision=record.revision + 1,
            updated_at=self._clock(),
            expires_at=None,
        )
        self._store.replace(updated, expected_revision)
        self._store.audit(updated, "confirmed", updated.updated_at)
        self._store.commit()
        return updated

    def complete(self, memory_id: str, *, expected_revision: int) -> MemoryRecord:
        self._require_enabled()
        record = self._required(memory_id)
        self._check_revision(record, expected_revision)
        if (
            record.category is not MemoryCategory.COMMITMENT
            or record.status is not MemoryStatus.ACTIVE
        ):
            raise MemoryValidationError("Only active commitments can be completed")
        now = self._clock()
        updated = replace(
            record,
            completed_at=now,
            expires_at=now + COMPLETED_COMMITMENT_RETENTION,
            revision=record.revision + 1,
            updated_at=now,
        )
        self._store.replace(updated, expected_revision)
        self._store.audit(updated, "completed", now)
        self._store.commit()
        return updated

    def forget(self, memory_id: str, *, expected_revision: int) -> None:
        self._require_enabled()
        record = self._required(memory_id)
        self._check_revision(record, expected_revision)
        self._store.erase(memory_id, expected_revision, "forgotten", self._clock())
        self._store.commit()

    def _required(self, memory_id: str) -> MemoryRecord:
        self._store.purge_expired(self._clock())
        self._store.commit()
        record = self._store.get(memory_id)
        if record is None:
            raise MemoryNotFoundError(f"Memory {memory_id} was not found")
        return record

    @staticmethod
    def _check_revision(record: MemoryRecord, expected_revision: int) -> None:
        if record.revision != expected_revision:
            raise MemoryConflictError("Memory revision is stale")

    def _require_capacity(self) -> None:
        if self._store.count_active() >= MAX_ACTIVE_MEMORIES:
            raise MemoryCapacityError(
                "SophIA already has 1,000 active memories; review them before adding more"
            )

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise MemoryUnavailableError("Continuous memory is disabled")
