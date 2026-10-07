"""Public PE4 continuous-memory domain."""

from src.backend.core.continuous_memory.domain import (
    ContinuousMemoryError,
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
from src.backend.core.continuous_memory.service import ContinuousMemoryService

__all__ = [
    "ContinuousMemoryError",
    "ContinuousMemoryService",
    "MemoryCapacityError",
    "MemoryCategory",
    "MemoryConflictError",
    "MemoryNotFoundError",
    "MemoryOrigin",
    "MemoryRecord",
    "MemoryStatus",
    "MemoryUnavailableError",
    "MemoryValidationError",
]
