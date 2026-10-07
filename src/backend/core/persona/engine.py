"""Transport- and persistence-independent SophIA persona snapshot service."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from src.backend.core.context.compressor import COMPRESSED_MASTER_PROMPT, compress_state
from src.backend.core.context.macros import render_macros
from src.backend.core.persona.text import (
    sanitize_prompt_text,
    truncate_at_sentence,
    truncate_tokens,
)


class PersonaContractError(ValueError):
    """Raised when source data cannot satisfy the public persona contract."""


@dataclass(frozen=True, slots=True)
class PersonaSnapshot:
    """Versioned response consumed by desktop or HTTP adapters."""

    schema_version: int
    character_name: str
    system_prompt: str
    mood: str
    dynamic: bool
    revision: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PersonaEngine:
    """Build an immutable prompt snapshot from structural domain objects.

    ``character``, ``state`` and ``user`` are intentionally structural inputs:
    SQLAlchemy models, dataclasses and test doubles can all satisfy the contract
    without making this domain service depend on a persistence framework.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        card_max_tokens: int = 8000,
        user_profile_tokens: int = 100,
    ) -> None:
        if card_max_tokens < 1 or user_profile_tokens < 1:
            raise PersonaContractError("persona token limits must be positive")
        self._card_max_tokens = card_max_tokens
        self._user_profile_tokens = user_profile_tokens

    def build_snapshot(
        self,
        character: Any,
        state: Any = None,
        user: Any = None,
    ) -> PersonaSnapshot:
        name = str(getattr(character, "name", "") or "").strip()
        if not name:
            raise PersonaContractError("character.name must be a non-empty string")

        user_name = str(getattr(user, "name", "User") or "User").strip() or "User"
        nickname = str(getattr(character, "nickname", "") or "").strip()
        display_name = nickname or name
        live_names = (user_name, name, display_name)
        state_data = self._state_mapping(state)

        sections = [COMPRESSED_MASTER_PROMPT]
        description = (
            getattr(character, "short_description", None)
            or getattr(character, "description", None)
            or ""
        )
        clean_description = self._card_text(description, name, user_name, live_names)
        identity = display_name
        if clean_description:
            identity += f". {clean_description}"
        sections.append(f"Identity: {identity}")

        self._append_card_section(
            sections,
            "Personality",
            getattr(character, "persona_prompt", ""),
            name,
            user_name,
            live_names,
        )
        self._append_card_section(
            sections,
            "Scenario",
            getattr(character, "scenario", ""),
            name,
            user_name,
            live_names,
        )

        modifiers = self._modifiers(character, live_names)
        if modifiers:
            sections.append("Behavior modifiers:\n" + modifiers)

        user_profile = self._user_profile(user, user_name, live_names)
        if user_profile:
            sections.append(user_profile)

        current_state = sanitize_prompt_text(
            compress_state(state_data, user_name), live_names
        )
        sections.append("Current state: " + current_state)

        examples = getattr(character, "mes_example", "") or ""
        if examples:
            # Role labels are intentional few-shot syntax in example dialogue.
            rendered = render_macros(examples, name, user_name)
            sections.append(
                "Example dialogue:\n"
                + truncate_at_sentence(rendered, self._card_max_tokens)
            )

        mood = sanitize_prompt_text(state_data.get("mood", "Neutral"), live_names)
        revision = self._revision(state)
        dynamic = getattr(character, "dynamic_persona", True)
        return PersonaSnapshot(
            schema_version=self.SCHEMA_VERSION,
            character_name=display_name,
            system_prompt="\n\n".join(section for section in sections if section),
            mood=mood or "Neutral",
            dynamic=True if dynamic is None else bool(dynamic),
            revision=revision,
        )

    @staticmethod
    def _state_mapping(state: Any) -> dict[str, Any]:
        if state is None:
            return {}
        if isinstance(state, Mapping):
            return dict(state)
        return {
            "location": getattr(state, "location", "Unknown"),
            "mood": getattr(state, "mood", "Neutral"),
            "clothes": getattr(state, "clothes", "Casual"),
            "stats": getattr(state, "stats", None),
        }

    @staticmethod
    def _revision(state: Any) -> int:
        if state is None or isinstance(state, Mapping):
            raw = state.get("version", 0) if isinstance(state, Mapping) else 0
        else:
            raw = getattr(state, "version", 0)
        try:
            return max(0, int(raw or 0))
        except (TypeError, ValueError):
            return 0

    def _card_text(
        self,
        value: Any,
        character_name: str,
        user_name: str,
        live_names: tuple[str, ...],
    ) -> str:
        rendered = render_macros(value, character_name, user_name)
        clean = sanitize_prompt_text(rendered, live_names)
        return truncate_at_sentence(clean, self._card_max_tokens)

    def _append_card_section(
        self,
        sections: list[str],
        heading: str,
        value: Any,
        character_name: str,
        user_name: str,
        live_names: tuple[str, ...],
    ) -> None:
        clean = self._card_text(value, character_name, user_name, live_names)
        if clean:
            sections.append(f"{heading}: {clean}")

    @staticmethod
    def _modifiers(character: Any, live_names: tuple[str, ...]) -> str:
        lines: list[str] = []
        for tag in getattr(character, "tags", None) or ():
            label = sanitize_prompt_text(getattr(tag, "label", ""), live_names)
            instruction = sanitize_prompt_text(
                getattr(tag, "instruction", ""), live_names
            )
            if label and instruction:
                lines.append(f"[{label}]: {instruction}")
        return "\n".join(lines)

    def _user_profile(
        self,
        user: Any,
        user_name: str,
        live_names: tuple[str, ...],
    ) -> str:
        if user is None:
            return ""
        parts: list[str] = []
        gender = getattr(user, "gender", "") or ""
        if gender and gender != "Unknown":
            parts.append("Gender: " + sanitize_prompt_text(gender, live_names))
        appearance = getattr(user, "appearance", "") or ""
        if appearance:
            parts.append("Appearance: " + sanitize_prompt_text(appearance, live_names))
        description = getattr(user, "persona_description", "") or ""
        if description:
            parts.append("Persona: " + sanitize_prompt_text(description, live_names))
        if not parts:
            return ""
        return truncate_tokens(
            f"User ({user_name}): " + " | ".join(parts),
            self._user_profile_tokens,
        )
