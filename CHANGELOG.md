# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to adhere to [Semantic Versioning](https://semver.org/)
once it starts tagging releases.

No version has been tagged yet (`git tag` is currently empty), so there is no
released history to enumerate. Everything below is the accumulated state of
`main`, grouped by theme and derived from the real commit history rather than
from invented version numbers or dates. As tagged releases start happening,
entries will move out of *Unreleased* into dated version sections.

## [Unreleased]

### Added
- SophIA Persona API 1.2 action-context contract for personality-shaped,
  result-first narration of bounded `open_url` and `remember_memory` facts.
- Selective continuous-memory API and turn-context retrieval for the one
  continuous SophIA identity.
- Living Entity Framework (E.P.I.C.) prompt overhaul: compressed master prompt,
  dual-position recency anchor, per-turn scene extraction, dynamic/static
  persona toggle, and a card-authoring guide (`docs/card-authoring-epic.md`).
- RAG memory pipeline: cosine+recency-blended retrieval ranking, near-duplicate
  dedup, relevance-threshold gating, and LLM-driven consolidation of aging
  memories when a per-scope cap is exceeded.
- Independent per-chat persona/storylines, with an explicit sync between the
  persistent `AgentState` and the active `Chat`'s conversation-local fields.
- Lorebook system: keyword-activated lore entries with `scan_depth`,
  `secondary_keys`, and per-entry cooldown to stop repeated per-turn re-injection.
- Alembic migration framework for schema evolution, alongside the existing
  manual-`ALTER TABLE` compatibility path in `init_db()`.
- Settings UI for `llama-server` configuration, including a consolidated
  inference+embedding mode and model selection.
- Mobile UX overhaul: layout responsiveness, PWA support (`vite-plugin-pwa`),
  offline font self-hosting, and mobile-specific Playwright coverage
  (`mobile-layout.spec.ts`, `mobile-chat-interactions.spec.ts`).
- Two GitHub Actions workflows: `qa.yml` (Ruff lint/format, backend pytest with
  an 80% coverage floor on both Ubuntu and Windows runners, frontend
  lint/build/Vitest coverage) and `e2e.yml` (Playwright E2E suite plus a
  built-frontend smoke test), both running on push/PR to `main` and nightly.

### Changed
- Reworked memory-cycle documentation (`docs/architecture.md`,
  `docs/data-model-er.md`) to track the E.P.I.C. overhaul.
- Tag evolution now layers relationship "warmth" instead of deleting
  author-defined tags.
- History window is capped independently of the model's full context size, so
  a small local model stays coherent even at large context configurations.

### Fixed
- Message edit/delete/regenerate now target the *owning* chat's row instead of
  the live, possibly-foreground `AgentState`, preventing pointer corruption
  when editing a background conversation.
- Vector-store persistence is now atomic (crash-safe dump), so an interrupted
  write can no longer corrupt stored memories.
- Reflection scheduling is checkpoint-based (`interaction_count -
  last_reflected_at_count`) instead of modulo-based, so a failed reflection at
  a boundary turn is retried instead of skipped forever.
- Lorebook keys now match on word boundaries, avoiding false-positive
  substring activations.
- `evolve_character` retries on `StaleDataError` under concurrent writes
  instead of silently losing the update.

### Documentation
- Added architecture, ADR, data-model, testing, compliance (LGPD/GDPR), and
  requirements documentation under `docs/`.
- Corrected `docs/infrastructure/ci-cd.md`, which previously stated no cloud
  CI existed — two real GitHub Actions workflows (`qa.yml`, `e2e.yml`) do.
- Corrected `docs/requirements/non-functional.md`, which stated an unverified
  99.9% uptime target with no monitoring infrastructure behind it.
- Added an English `README.md` and a `README.pt-BR.md` Portuguese variant,
  `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates,
  and this changelog.
- Restructured internal docs into two mirrored language trees, `docs/en/` and
  `docs/pt-BR/` (same filenames, same structure), with `docs/README.md` as a
  short language index. Language-neutral assets (`api/openapi.yaml`, the `.puml`
  diagram sources) live only under `docs/en/` and are linked from both trees.
  Added a consolidated `setup/quickstart.md` in both languages. Historical
  working documents (superseded audits/plans, `docs/superpowers/`,
  `docs/figma/`) were intentionally left in place, untranslated.
