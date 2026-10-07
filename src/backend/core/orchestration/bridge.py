import json
import logging
import re
from difflib import SequenceMatcher
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.backend.core.memory.vector_store import VectorStore
from src.backend.db.models import Tag
from langchain_core.prompts import PromptTemplate
from src.backend.core.context.compressor import COMPRESSED_MASTER_PROMPT, compress_state
from src.backend.core.context.budget import ContextBudgetCalculator
from src.backend.core.config import settings
from src.backend.core.context.macros import render_macros
from src.backend.core.persona.text import (
    sanitize_prompt_text,
    truncate_at_sentence,
    truncate_tokens,
)

logger = logging.getLogger(__name__)

REFLECTION_GRAMMAR = r"""
root ::= "{" space "\"summary\"" ":" space string "," space "\"facts\"" ":" space list "," space "\"traits\"" ":" space list "," space "\"relationship_change\"" ":" space number "," space "\"location\"" ":" space string "," space "\"mood\"" ":" space string "," space "\"diary_entry\"" ":" space string space "}"
list ::= "[" space (string ("," space string)*)? space "]"
string ::= "\"" ([^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])* "\""
number ::= "-"? [0-9]+
space ::= [ \t\n\r]*
"""

# Tiny grammar for the cheap per-turn scene tracker (EPIC Phase 2): just the
# current location + mood, so it stays far lighter than a full reflection.
SCENE_GRAMMAR = r"""
root ::= "{" space "\"location\"" ":" space string "," space "\"mood\"" ":" space string space "}"
string ::= "\"" ([^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])* "\""
space ::= [ \t\n\r]*
"""

# The ultra-compact Prompt Template (Plain Text, no redundant markdown headers)
ENTITY_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "{master_prompt}\n\n"
    "Identity: {identity}\n"
    "{persona_str}"
    "{scenario_str}"
    "{modifiers}\n"
    "{user_persona}\n"
    "{state_str}\n\n"
    "Memories:\n{context}{lore_context}\n"
    "{summary_context}\n"
    "{example_dialogs_str}"
    "History:\n{history_str}\n\n"
    "{user_info}: {user_message}\n\n"
    "{anchor}\n"
    "Reply:"
)


_MEMORY_REDUNDANT_RATIO = 0.9


def _norm(text: Any) -> str:
    """Lowercase + collapse whitespace, for cheap text-overlap checks."""
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def _memory_redundant_with_recent(doc: str, recent_lines: List[str]) -> bool:
    """A stored memory is written as 'User: {msg}\\nAI: {reply}'. It is redundant
    only if EACH of its halves near-matches (>= _MEMORY_REDUNDANT_RATIO) some
    single recent history/summary line -- i.e. that exact turn is already visible
    and re-injecting it just duplicates context (RQ-02).

    Matching against discrete lines (not a substring of the concatenated blob)
    is deliberate: a short/common half like 'ok', or a distinct earlier turn
    whose text happens to be a substring of some unrelated later line, must NOT
    be dropped. Coupled to the storage format on purpose; if that changes this
    degrades to a harmless no-op. `recent_lines` are already _norm'd."""
    if not doc or not recent_lines:
        return False
    # maxsplit=1 on the first 'ai:' can mis-split a memory whose USER half itself
    # contains 'ai:'; that only ever weakens a half's match (-> memory kept), so
    # it can cause a missed drop but never a wrong drop.
    parts = re.split(r"\bai\s*:\s*", doc, maxsplit=1, flags=re.IGNORECASE)
    user_half = re.sub(r"^\s*user\s*:\s*", "", parts[0], flags=re.IGNORECASE)
    halves = [user_half] + (parts[1:] if len(parts) > 1 else [])
    normed = [_norm(h) for h in halves if _norm(h)]
    if not normed:
        return False

    def _present(half: str) -> bool:
        return any(
            SequenceMatcher(None, half, line).ratio() >= _MEMORY_REDUNDANT_RATIO
            for line in recent_lines
        )

    return all(_present(h) for h in normed)


class Brain:
    def __init__(self, vector_store: VectorStore, llm_client=None):
        self.vector_store = vector_store
        self.llm = llm_client or vector_store.llm_client
        self.budget_calc = ContextBudgetCalculator(llama_url=self.llm.url)

    @staticmethod
    def _sanitize(text: Any, extra_names=()) -> str:
        """Neutralize role/boundary markers in free-text card/persona fields so a
        crafted value can't forge fake dialogue turns or a premature 'Reply:'
        cutoff. The colon-strip after any role keyword (incl. the live user/char
        name) is what actually blocks forgery -- a bare '\\nUser hi' can't be
        parsed as a turn -- so newlines are PRESERVED. A card's section headers
        and bullet lists (a real characterization lever for small models) then
        survive instead of being flattened into a run-on paragraph (A2)."""
        return sanitize_prompt_text(text, extra_names)

    @staticmethod
    def _truncate_tokens(text: Any, max_tokens: int, from_end: bool = False) -> str:
        """Hard-cap a layer to ~max_tokens (1 tok ~ 4 chars) so an oversized
        field can't blow past context_size and push the master prompt off the
        top of the window. `from_end=True` keeps the TAIL (most recent) instead
        of the head -- used for the rolling summary, whose newest lines matter
        most (RF-05)."""
        return truncate_tokens(text, max_tokens, from_end)

    def _build_anchor(
        self,
        character: Any,
        state: Dict[str, Any],
        user_name: str,
        char_display_name: str,
    ) -> str:
        """Recency anchor (E.P.I.C. Phase 1): a compact persona-voice + current-
        scene reminder re-injected right before 'Reply:', so a small model reads
        WHO it is and WHERE it is as the very last thing before generating.
        Recency beats the lost-in-the-middle of a long context window. Derived
        from the existing card fields -- no new schema -- so it is only as strong
        as the card is filled."""
        name = char_display_name or (character.name if character else "the character")
        # Sanitize the essence with the SAME live names as the main body (user +
        # char + display name), not just the generic role markers. With newlines
        # now preserved (A2), a crafted/imported card must not be able to forge a
        # "{char}:"/"{user}:" turn HERE, in the highest-recency slot right before
        # Reply: -- the main body strips those markers, so the anchor must too.
        char_name = character.name if character else ""
        _names = tuple(n for n in (user_name, char_name, char_display_name) if n)
        essence = ""
        if character:
            raw = (
                getattr(character, "persona_prompt", None)
                or getattr(character, "short_description", None)
                or getattr(character, "description", None)
                or ""
            )
            if raw:
                essence = self._truncate_at_sentence(
                    self._sanitize(render_macros(raw, name, user_name), _names), 60
                )
        loc = (state or {}).get("location") or "Unknown"
        mood = (state or {}).get("mood") or "Neutral"
        parts = [f"[Stay in character] You are {name}."]
        if essence:
            essence = essence.rstrip()
            parts.append(
                essence if essence.endswith((".", "!", "?", "…")) else essence + "."
            )
        parts.append(f"Right now: {loc}; mood {mood}.")
        parts.append(
            f"Reply in-voice as {name}: react to what {user_name} just said, drive the tension, end with a hook."
        )
        return self._truncate_at_sentence(" ".join(parts), settings.ANCHOR_TOKENS)

    @staticmethod
    def _truncate_at_sentence(text: Any, max_tokens: int) -> str:
        """Cap a free-text card field to ~max_tokens, but cut at the last
        sentence boundary inside the window instead of mid-word, so a truncated
        persona still ends on a complete thought. Falls back to a hard char cut
        only when no sentence break sits in the back half of the window. Used for
        the card layers (persona/scenario/description/examples), whose HARD
        ceiling is settings.CARD_MAX_TOKENS -- generous, so a normal card is
        never touched; the cut only fires on a pathologically long field."""
        return truncate_at_sentence(text, max_tokens)

    async def build_prompt(
        self,
        user_message: str,
        character: Any,
        state: Dict[str, Any],
        user: Any = None,
        history: List[Any] = None,
        db: Session = None,
        chat_id: Any = None,
        interaction_count: int = 0,
        lore_cooldowns: Dict[str, Any] = None,
    ) -> str:
        """Assembles the ultra-compact 6-layer prompt for models 1-4B using Token Budgeting."""
        budget = await self.budget_calc.get_budget()

        # Layer 1: Memories (RAG). Scope to (character, chat) so one chat/session
        # never retrieves another's memories. Legacy memories with no chat_id
        # simply won't match the exact-match filter -> no cross-chat poison.
        memory_filter = None
        if character:
            memory_filter = {"character_id": character.id}
            if chat_id is not None:
                memory_filter["chat_id"] = chat_id
        context_data = await self.vector_store.query_memory(
            user_message,
            metadata_filter=memory_filter,
        )
        # Raw docs captured here; the injectable string is assembled below once
        # _names is known, so memories get the same sanitize+cap as every other
        # free-text layer (PZ-05).
        memory_docs = []
        if isinstance(context_data, dict) and context_data.get("documents"):
            memory_docs = context_data["documents"][0] or []

        allocations = budget.get("allocations", {})

        # Layer 1.5: Lorebooks (Keyword-triggered via Regex Scanner V2)
        lore_context = ""
        if db and character:
            from src.backend.core.context.lorebook_scanner import LorebookScanner

            scanner = LorebookScanner(db)
            hist_texts = [
                (m.get("content") if isinstance(m, dict) else getattr(m, "content", ""))
                or ""
                for m in (history or [])
            ]
            active_lore = scanner.scan_and_extract(
                user_message,
                character.id,
                history=hist_texts,
                turn_index=interaction_count,
                cooldowns=lore_cooldowns,
            )
            if active_lore:
                lore_text = "\n".join([f"- {self._sanitize(d)}" for d in active_lore])
                lore_text = self._truncate_tokens(
                    lore_text, allocations.get("lorebook_cap", 500)
                )
                lore_context = "\nLore:\n" + lore_text

        # Layer 1.5: Summary (raw here; sanitized + assembled below once _names
        # is known, so the LLM-generated summary can't forge role markers, PZ-06).
        raw_summary = state.get("active_summary", "") if state else ""

        # Layer 2: History (Dynamic Sliding Window)
        user_name = user.name if user else "User"
        char_name = character.name if character else "You"

        history_lines = []
        if history:
            for msg in history:
                role_val = (
                    msg["role"] if isinstance(msg, dict) else getattr(msg, "role", "")
                )
                role = user_name if role_val == "user" else char_name
                content = (
                    msg.content if hasattr(msg, "content") else msg.get("content", "")
                )
                history_lines.append(f"{role}: {content}")

        # Enforce budget for history
        history_str = ""
        if history_lines:
            history_budget = budget.get("history_budget", 2048)  # Default fallback
            # Aggregate-card guard: the per-field CARD_MAX cap bounds each card
            # field but NOT their sum, and the fixed reserve can under-count a big
            # card. Shave any real card overage off history so card + fixed layers
            # + history stay inside the window even on a small/edited context.
            # No-op when there is slack (e.g. the shipped 48k) since history stays
            # capped at its window, below the ceiling. Gated on usable_budget so
            # it never misfires when a caller mocks a partial budget.
            _usable = budget.get("usable_budget")
            if character and _usable is not None:
                _cap = settings.CARD_MAX_TOKENS * 4

                def _est(v):
                    return min(len(str(v or "")), _cap) // 4

                card_est = (
                    _est(getattr(character, "persona_prompt", ""))
                    + _est(getattr(character, "scenario", ""))
                    + _est(
                        getattr(character, "short_description", None)
                        or getattr(character, "description", None)
                    )
                    + _est(getattr(character, "mes_example", ""))
                )
                _fixed = sum(allocations.values()) if allocations else 0
                _card_reserve = allocations.get("character_def", 0) + allocations.get(
                    "mes_example", 0
                )
                ceiling = (_usable - _fixed) + _card_reserve - card_est
                history_budget = max(0, min(history_budget, ceiling))
            current_tokens = 0
            allowed_lines = []

            # Start from the most recent (end of list) and go backwards
            for idx, line in enumerate(reversed(history_lines)):
                # Approximation for speed: 1 token ~ 4 chars
                est_tokens = len(line) // 4 + 5
                if current_tokens + est_tokens <= history_budget:
                    allowed_lines.insert(0, line)
                    current_tokens += est_tokens
                elif idx == 0:
                    # The most recent turn is the single most important line for
                    # continuity -- never drop it wholesale. Hard-truncate its
                    # head to fit (small floor so a tiny budget still yields a
                    # usable fragment), keeping the leading role marker.
                    keep_chars = max(history_budget * 4, 240)
                    allowed_lines.insert(0, line[:keep_chars])
                    break
                else:
                    break
            history_str = "\n".join(allowed_lines)

        # Layer 3: Identity & Tags & Persona.
        # All free-text card/persona fields are sanitized so a crafted value
        # cannot forge role markers ("User:", "Reply:", char/user name + ":").
        char_display_name = (
            character.nickname
            if (character and getattr(character, "nickname", None))
            else (character.name if character else "You")
        )
        _names = (user_name, char_name, char_display_name)

        # Layer 1 (assembled now that _names is known): retrieved memories are
        # sanitized -- a stored memory can contain "User:"/"Reply:" markers +
        # newlines and would otherwise forge dialogue turns -- and length-capped
        # so they can't overflow the context window (PZ-05).
        context = "None."
        if memory_docs:
            # Drop memories that just replay a turn already visible in the recent
            # history/summary -- injecting them again duplicates context and
            # over-weights that moment (RQ-02). Compare against discrete lines so
            # a distinct memory isn't dropped for coincidentally overlapping
            # unrelated text.
            recent_lines = [
                _norm(
                    (
                        m.get("content")
                        if isinstance(m, dict)
                        else getattr(m, "content", "")
                    )
                    or ""
                )
                for m in (history or [])
            ]
            recent_lines += [_norm(ln) for ln in (raw_summary or "").splitlines()]
            recent_lines = [ln for ln in recent_lines if ln]
            fresh_docs = [
                d
                for d in memory_docs
                if d and not _memory_redundant_with_recent(str(d), recent_lines)
            ]
            sanitized = [self._sanitize(str(d), _names) for d in fresh_docs if d]
            joined = " ".join(s for s in sanitized if s)
            if joined:
                context = self._truncate_tokens(joined, allocations.get("memory", 400))

        summary_context = ""
        if raw_summary:
            clean_summary = self._truncate_tokens(
                self._sanitize(raw_summary, _names),
                allocations.get("chat_summary", 200),
                from_end=True,
            )
            if clean_summary:
                summary_context = f"\nSummary:\n{clean_summary}\n"
        # Cap each free-text card field only at the generous per-field safety
        # ceiling (settings.CARD_MAX_TOKENS) so a normal rich card survives whole
        # -- the old 300-token guillotine chopped real personas to ~225 words and
        # was a top cause of "the character reads generic". Cut at a sentence
        # boundary, not mid-word, if the ceiling is ever hit (PB-01 safety kept).
        _card_cap = settings.CARD_MAX_TOKENS
        short_desc = (
            getattr(character, "short_description", None)
            or getattr(character, "description", None)
            or ""
        )
        short_desc = self._truncate_at_sentence(
            self._sanitize(render_macros(short_desc, char_name, user_name), _names),
            _card_cap,
        )
        identity = (
            f"{char_display_name}. {short_desc}" if character else "You are unique."
        )

        persona_str = ""
        if character and getattr(character, "persona_prompt", None):
            persona = self._truncate_at_sentence(
                self._sanitize(
                    render_macros(character.persona_prompt, char_name, user_name),
                    _names,
                ),
                _card_cap,
            )
            persona_str = f"Personality: {persona}\n"

        scenario_str = ""
        if character and getattr(character, "scenario", None):
            scenario = self._truncate_at_sentence(
                self._sanitize(
                    render_macros(character.scenario, char_name, user_name), _names
                ),
                _card_cap,
            )
            scenario_str = f"Scenario: {scenario}\n"

        example_dialogs_str = ""
        if character and getattr(character, "mes_example", None):
            # mes_example is few-shot dialogue: its role labels ("{{char}}:",
            # "{{user}}:") are the intended format, and it's authored at the same
            # trust level as the rest of the card -- so resolve macros and cap
            # its length, but do NOT sanitize role markers out of it.
            example = self._truncate_at_sentence(
                render_macros(character.mes_example, char_name, user_name),
                settings.CARD_MAX_TOKENS,
            )
            example_dialogs_str = f"Example Dialogs:\n{example}\n\n"

        tags = []
        if character and character.tags:
            for t in character.tags:
                tags.append(
                    f"[{self._sanitize(t.label, _names)}]: {self._sanitize(t.instruction, _names)}"
                )

        user_persona = ""
        if user:
            persona_parts = []
            if user.gender and user.gender != "Unknown":
                persona_parts.append(f"Gender: {self._sanitize(user.gender, _names)}")
            if getattr(user, "appearance", None):
                persona_parts.append(
                    f"Appearance: {self._sanitize(user.appearance, _names)}"
                )
            if getattr(user, "persona_description", None):
                persona_parts.append(
                    f"Persona: {self._sanitize(user.persona_description, _names)}"
                )
            if persona_parts:
                user_persona = self._truncate_tokens(
                    f"User ({user_name}): " + " | ".join(persona_parts),
                    allocations.get("user_persona", 100),
                )

        # Layer 4: State (Compressed)
        state_str = compress_state(state, user_name)

        # Format via LangChain PromptTemplate
        return ENTITY_PROMPT_TEMPLATE.format(
            master_prompt=COMPRESSED_MASTER_PROMPT,
            identity=identity,
            persona_str=persona_str,
            scenario_str=scenario_str,
            example_dialogs_str=example_dialogs_str,
            modifiers="\n".join(tags),
            user_persona=user_persona,
            state_str=state_str,
            context=context,
            lore_context=lore_context,
            summary_context=summary_context,
            history_str=history_str,
            user_info=user_name,
            user_message=user_message,
            anchor=self._build_anchor(character, state, user_name, char_display_name),
        )

    async def reflect(self, messages: List[Dict], window_size: int = 20) -> Dict:
        """Analyzes interaction for summary, facts, traits, relationship change, and diary entry."""
        prompt = (
            "Analyze the interaction. Extract a summary, new facts about the user, character trait updates, "
            "a relationship_change integer (ranging from -5 to +5) representing how much the user's bonding progress "
            "improved or declined based on their tone (positive/friendly = positive change, hostile/cold = negative change), "
            "the character's CURRENT 'location' (a short place name, e.g. 'Kitchen', 'Rooftop garden') and current 'mood' "
            "(one or two words) as they are by the end of these turns, "
            "and a 'diary_entry' string containing a 2-3 sentence diary entry written in the first person from the character's "
            "perspective. The diary entry must express their raw inner thoughts, emotional state, insecurities, or feelings of closeness "
            "regarding the user based on these recent interactions. JSON ONLY.\n\n"
        )
        for msg in messages[-window_size:]:
            role = (
                msg["role"].capitalize()
                if isinstance(msg, dict)
                else getattr(msg, "role", "").capitalize()
            )
            content = (
                msg["content"] if isinstance(msg, dict) else getattr(msg, "content", "")
            )
            prompt += f"{role}: {content}\n"

        result = await self.llm.complete(prompt, grammar=REFLECTION_GRAMMAR)
        return self._safe_json_parse(result.get("content", "{}"))

    async def extract_scene(
        self,
        reply_text: str,
        current_location: str = "Unknown",
        current_mood: str = "Neutral",
    ) -> Dict:
        """Cheap per-turn scene tracker (EPIC Phase 2): read the latest narration
        and report the character's CURRENT location + mood at the end of it, so
        the HUD and recency anchor follow the scene EVERY turn instead of only on
        the 20-turn reflection (the reason a move like 'takes the elevator down'
        never updated the location). Short prompt (just the reply), grammar-
        constrained, decoupled from reflect()."""
        if not reply_text or not str(reply_text).strip():
            return {}
        prompt = (
            "From this narration, output the character's CURRENT location (a short "
            "place name, e.g. 'Kitchen', 'Elevator', 'Lobby') and current mood "
            "(one or two words) as they are at the END of it. If the scene did not "
            f"move, repeat the current values. Current location: {current_location}. "
            f"Current mood: {current_mood}. JSON ONLY.\n\nNarration:\n{reply_text}\n\nJSON:"
        )
        result = await self.llm.complete(prompt, grammar=SCENE_GRAMMAR)
        data = self._safe_json_parse(result.get("content", "{}"))
        return data if isinstance(data, dict) else {}

    async def suggest_tags(self, description: str, db: Session) -> List[int]:
        """Suggests appropriate personality tag IDs based on description."""
        all_tags = db.query(Tag).all()
        if not all_tags:
            return []

        tag_list = "\n".join([f"ID {t.id}: {t.label}" for t in all_tags])
        prompt = f"Select tag IDs for this character description. JSON list ONLY.\n\nDESC: {description}\n\nTAGS:\n{tag_list}"

        result = await self.llm.complete(prompt)
        ids = self._safe_json_parse(result.get("content", "[]"))
        valid_ids = {t.id for t in all_tags}
        return [i for i in ids if i in valid_ids] if isinstance(ids, list) else []

    def _safe_json_parse(self, content: str) -> Any:
        """Cleans and parses JSON from LLM response."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"JSON Parse failed: {e}")
            return {}
