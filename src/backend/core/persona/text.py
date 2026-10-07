"""Shared prompt-text guards used by the persona and chat runtimes."""

from __future__ import annotations

import re
from typing import Any, Iterable

_ROLE_MARKERS = (
    "reply",
    "user",
    "assistant",
    "system",
    "you",
    "human",
    "ai",
    "char",
    "character",
)


def sanitize_prompt_text(text: Any, extra_names: Iterable[object] = ()) -> str:
    """Neutralize forged role boundaries while preserving card structure."""
    if not text:
        return ""

    normalized = re.sub(r"\r\n?", "\n", str(text))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    markers = list(_ROLE_MARKERS) + [str(name).lower() for name in extra_names if name]
    pattern = r"(?i)\b(" + "|".join(re.escape(marker) for marker in markers) + r")\s*:"
    return re.sub(pattern, lambda match: match.group(1) + " ", normalized).strip()


def truncate_tokens(text: Any, max_tokens: int, from_end: bool = False) -> str:
    """Bound text using the runtime's inexpensive four-characters/token estimate."""
    if not text:
        return ""

    value = str(text)
    max_chars = max(0, int(max_tokens) * 4)
    if len(value) <= max_chars:
        return value
    if from_end:
        return "[…] " + value[-max_chars:].lstrip()
    return value[:max_chars].rstrip() + " […]"


def truncate_at_sentence(text: Any, max_tokens: int) -> str:
    """Bound card text, preferring a complete sentence near the limit."""
    if not text:
        return ""

    value = str(text)
    max_chars = max(0, int(max_tokens) * 4)
    if len(value) <= max_chars:
        return value

    window = value[:max_chars]
    cut = max(
        window.rfind(". "),
        window.rfind("! "),
        window.rfind("? "),
        window.rfind(".\n"),
        window.rfind("\n"),
    )
    if cut > max_chars // 2:
        return window[: cut + 1].rstrip() + " […]"
    return window.rstrip() + " […]"
