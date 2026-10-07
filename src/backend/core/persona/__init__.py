"""Headless personality contract for SophIA integrations."""

from src.backend.core.persona.engine import (
    PersonaContractError,
    PersonaEngine,
    PersonaSnapshot,
)

__all__ = ["PersonaContractError", "PersonaEngine", "PersonaSnapshot"]
