# Architecture

Open-ChatBot is a local, self-hosted, single-user stateful AI character/RP engine.
FastAPI + SQLAlchemy + SQLite backend, React + TS + Vite frontend, and a local
`llama-server` (llama.cpp) providing both inference and embeddings. This describes
the flows that span many files; for the schema see [data-model-er.md](./data-model-er.md).

## Composition root

App-wide singletons `llama_client`, `vector_store`, `brain` are built once in
`core/deps.py` and imported everywhere. Never construct your own — separate
instances mean divergent in-memory vector stores over the same path, so a memory
added via one is invisible to another until restart.

The SophIA Persona API has a separate, minimal composition root:
`core/persona/deps.py` owns its domain singleton and `persona_main.py` starts a
loopback-only FastAPI service with persistence but no LLM, RAG, frontend, or
speech runtime. This boundary does not change the legacy chat application flow.
See [ADR-006](architecture/decisions/adr-006.md).

## The chat turn

```mermaid
sequenceDiagram
    participant C as Client
    participant API as api/chat.py
    participant Brain as Brain.build_prompt
    participant LL as llama-server
    participant BG as run_consciousness_layer (bg)
    C->>API: POST /chat or /chat/stream
    API->>API: _prepare_chat_turn: resolve user/character/state/chat
    API->>API: need-decay (dynamic only) + action deltas; validate parent_id
    API->>API: persist user message; walk active-branch history
    API->>Brain: build_prompt(state, history, lore, memory, budget)
    Brain->>LL: query_memory (RAG) + tokenize (budget)
    API->>LL: complete / complete_stream
    LL-->>API: reply
    API->>API: parse_actions_to_state; _persist_assistant_reply (retry on StaleData)
    API->>BG: schedule run_consciousness_layer
    BG->>LL: store memory; extract_scene (every turn); on interval, reflect + evolve
```

`_prepare_chat_turn` is shared by both `POST /chat` and `POST /chat/stream` so the
two paths can't diverge. Reflection is checkpoint-based:
`force_reflect = interaction_count - last_reflected_at_count >= REFLECTION_INTERVAL`
(a failed boundary reflection is retried, not skipped forever).

**Per-turn scene tracking.** After every turn `run_consciousness_layer` runs a
cheap scene extractor — `Brain.extract_scene` (a tiny GBNF `SCENE_GRAMMAR` over
just the latest reply → `{location, mood}`) followed by
`engine.apply_scene_update` (mirror-aware, same `with_for_update` +
`StaleDataError`-retry pattern as `evolve_character`). This is **decoupled** from
the 20-turn reflection so a move like *"takes the elevator down"* updates the HUD
and recency anchor immediately instead of only on the next reflection boundary.
It is skipped under pytest (like the llama boot) and any failure is non-fatal —
the turn already succeeded.

**Dynamic vs. static persona.** `Character.dynamic_persona` (boolean, default
`True`) gates the simulation in `_prepare_chat_turn`. Dynamic (default) runs
need-decay and reflection-driven evolution; static freezes the persona exactly as
authored (no decay, no drift) — `force_reflect` and `update_needs` are both
suppressed. Scene tracking and memory recall run in **both** modes; only the
persona-mutating simulation is gated. A legacy row with a `NULL` flag defaults to
dynamic.

## Two-layer state (the mirror)

A character has one `AgentState` holding the **live** persona; each `Chat` is a
separate storyline and the **canonical** store of its conversation-local fields +
persona snapshot. `AgentState` mirrors the active chat; switching saves the
outgoing snapshot and restores the incoming one. Persona is **per-chat** (B8):
independent storylines. See [data-model-er.md](./data-model-er.md) §2.

## Memory lifecycle (anti-poison)

- **Scope:** every memory, history walk, and journal is scoped to
  `(character_id, chat_id)` so one chat can never poison another.
- **Storage:** RAG memories live in a turbovec store on disk (not the relational
  DB), linked to messages only by `message_id` metadata. Purged manually on
  edit/delete/regenerate.
- **Retrieval (`query_memory`):** over-fetch → relevance-threshold gate →
  cosine+recency blended re-rank → near-duplicate dedup → drop memories already
  visible in recent history. Results assembled into the prompt are sanitized
  against role-marker injection and length-capped.
- **Bounding:** when a chat scope exceeds the cap, the oldest memories are
  condensed by the LLM into one consolidated memory (store-before-delete).
- **Durability:** `_atomic_dump` writes to a temp dir then swaps, so a crash
  can't leave a torn store.

## Prompt assembly (`core/orchestration/bridge.py`)

An ultra-compact layered prompt for small local models, token-budgeted by
`core/context/budget.py` (fixed per-layer caps + a history floor). `Brain.build_prompt`
fills `ENTITY_PROMPT_TEMPLATE` in this order: master prompt → identity/persona/
scenario/tags → user persona → compressed state → RAG memory + lorebook (regex keys
with word boundaries, scan_depth, secondary keys, cooldown) → rolling `active_summary`
→ example dialogs → history → the latest user message → **recency anchor** → `Reply:`.
Every free-text card/persona field is sanitized and length-capped.

**Master prompt (E.P.I.C. engagement mechanics).** `COMPRESSED_MASTER_PROMPT`
(`core/context/compressor.py`) is written around engagement, not word count: stay
in the character's exact voice/tics, react to and build on the user's last input,
drive and escalate a visible want/tension every turn, ground one sensory beat that
*acts on* the user, and end with a hook that invites a short reply — with adaptive
length matched to the user's energy. The old "living entity / 3-5 paragraphs /
don't rush" forced-length rule is gone.

**Dual-position persona anchor.** `Brain._build_anchor` re-injects a compact
"You are {name}. {persona-essence}. Right now: {location}; mood {mood}. Reply
in-voice; react; drive the tension; end with a hook." block **right before
`Reply:`**, so the persona sits at **both ends** of the prompt (primacy at the top
+ recency at the bottom). A ~4B model attends to the start and end and loses the
middle of a long window, so the current scene and voice are the last thing it
reads before generating. The anchor is derived from existing card fields (no new
schema) and capped at `settings.ANCHOR_TOKENS`.

**Sanitization preserves newlines.** `_sanitize` keeps line structure (only
normalizing endings and bounding blank runs) so a card's section headers and
bullet lists — a real characterization lever on small models — survive instead of
being flattened. The colon-strip after any role marker (incl. the live user/char
name) is what actually blocks turn-forgery / a premature `Reply:` cutoff (A2).

**Card caps.** Free-text card fields (persona/scenario/description/examples) are no
longer chopped at 300 tokens — that guillotine cut real personas to ~225 words and
was a top cause of "the character reads generic". They are now capped at the
generous `settings.CARD_MAX_TOKENS` (8000) via `_truncate_at_sentence` (cuts at a
sentence boundary, never mid-word, and only fires on a pathologically long field).
`settings.RECOMMENDED_CARD_TOKENS` (4096) is a soft UI hint only.

**History window.** Even on a large context (`models_config.json` now defaults to
`context_size` 49152 / 48k, up from 4096), raw history is bounded to
`settings.HISTORY_WINDOW_TOKENS` (10000) in `budget.py` — feeding ~40k of raw
turns buries the persona/anchor in the lost-in-the-middle zone. Turns older than
the window are carried by the rolling summary + RAG, not dumped raw.

**Compressed state (`compress_state`).** Relationship is expressed as a warmth
**dial** rendered "in your own voice" (cold / reserved / warm / close + score),
replacing the old generic `Rel(Acquaintance): Polite but reserved` label that
homogenized every character into one tone. Physiological modifiers are
bidirectional: energy ≥ 80 now reads as `ENERGIZED` (alert/animated), not only the
low-energy exhaustion warnings.

## Reflection / evolution (`core/engine/engine.py`)

`run_consciousness_layer` (background task) stores the turn's memory, runs the
per-turn scene extractor (above), and — only on interval and only for a
`dynamic_persona` character — calls `brain.reflect` (GBNF-constrained JSON) then
`evolve_character`. Evolution applies the reflection (relationship delta, facts,
traits, tag warmth-layering, rolling summary, journal, location/mood) inside a
`with_for_update` + version-guarded transaction with `StaleDataError` retries. If
the user switched chats during the slow reflect(), the reflection is applied to
the *reflecting* chat's snapshot, never the now-active one. `apply_scene_update`
follows the identical mirror-aware pattern for its lighter location/mood-only
write.

## llama-server runner (`core/engine/runner.py`)

Auto-starts a consolidated local llama-server (inference + embeddings on one port,
default 8080) from `models_config.json` on startup, health-gated with a warmup
poll. Bypassed entirely under pytest/E2E.

## Serving

`main.py` registers routers (chat, characters, tags, users, settings, lore,
presets) and mounts the built frontend from `static/` with an SPA catch-all — API
routes are registered before the catch-all.
