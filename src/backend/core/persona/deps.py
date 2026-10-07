"""Composition root for the headless persona domain service."""

from src.backend.core.persona.engine import PersonaEngine

_persona_engine = PersonaEngine()


def get_persona_engine() -> PersonaEngine:
    """Return the process-wide immutable Persona Engine configuration."""
    return _persona_engine
