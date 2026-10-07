# Open-ChatBot Documentation

Reference documentation for Open-ChatBot's architecture, data model, testing, requirements, and compliance posture. This tree mirrors [docs/pt-BR/](../pt-BR/) file-for-file; if a link here 404s in the Portuguese tree, that page hasn't been translated yet.

## Start here

* **[setup/quickstart.md](setup/quickstart.md)** — prerequisites and run steps, consolidated from the README and the run scripts.
* **[architecture.md](architecture.md)** — the turn-by-turn flow, the memory/reflection cycle, and the prompt-assembly pipeline. The most detailed architecture document in this repository; read this first for how a chat turn actually works.
* **[data-model-er.md](data-model-er.md)** — the relational schema plus the out-of-band vector memory store, and the non-obvious decisions behind them (the Chat↔AgentState mirror, per-chat persona, soft-delete-only history).
* **[testing.md](testing.md)** — running the test suites, isolation guarantees, and how to add a feature without breaking either.
* **[card-authoring-epic.md](card-authoring-epic.md)** — how to write a character card that makes a small local model perform well.

## Requirements

* **[requirements/ers.md](requirements/ers.md)** — Engineering Requirements Specification.
* **[requirements/functional.md](requirements/functional.md)** — functional requirements (RF-xxx).
* **[requirements/non-functional.md](requirements/non-functional.md)** — non-functional targets (RNF-xxx); read the Availability entry before quoting any uptime figure from this repo.
* **[requirements/business-rules.md](requirements/business-rules.md)** — business rules (RN-xxx).
* **[requirements/traceability-matrix.md](requirements/traceability-matrix.md)** — requirement-to-implementation traceability.

## Architecture

* **[architecture/overview.md](architecture/overview.md)** — high-level system drivers and component list, at a coarser grain than `architecture.md` above. The two documents were written at different times and different depths; `architecture.md` is the one to trust for how the prompt pipeline and memory cycle actually behave today, this one for a one-page orientation.
* **[architecture/decisions/](architecture/decisions/)** — Architecture Decision Records (ADR-002 database/persistence, ADR-003 local-first inference, ADR-004 language/orchestration, ADR-005 SophIA Persona Engine boundary, ADR-006 dedicated local Persona API).
* **[architecture/c4/](architecture/c4/)** — C4 context/container/component notes and diagram source.
* **[architecture/security.md](architecture/security.md)** — STRIDE threat model for the single-tenant, local-only deployment.

## Models

* **[models/domain-boundaries.md](models/domain-boundaries.md)** — DDD bounded contexts and the domain class diagram source.
* **[models/uml/overview.md](models/uml/overview.md)** — sequence/class/state diagrams.
* **[models/erd/README.md](models/erd/README.md)** — table-level ERD detail, a complementary view to `data-model-er.md` above.

## API

* **[api/openapi.yaml](api/openapi.yaml)** — the OpenAPI contract. Language-neutral; not duplicated into the Portuguese tree.
* **[api/persona-v1.openapi.yaml](api/persona-v1.openapi.yaml)** — the versioned, loopback-only SophIA Persona Engine contract.
* **[api/auth.md](api/auth.md)** — current auth model (there isn't one — single-tenant, loopback-bound, no middleware) and what production/multi-tenant deployment would require.

## Infrastructure & compliance

* **[infrastructure/ci-cd.md](infrastructure/ci-cd.md)** — the real CI quality gates (`.github/workflows/qa.yml`, `.github/workflows/e2e.yml`).
* **[infrastructure/sre.md](infrastructure/sre.md)** — local process management, health checks, and storage maintenance.
* **[compliance/lgpd.md](compliance/lgpd.md)** — LGPD/GDPR data-privacy posture for a fully local, offline-by-default application.
* **[compliance/audit.md](compliance/audit.md)** — the request-correlation-ID audit trail.

## Design & features

* **[design/immersion-guidelines.md](design/immersion-guidelines.md)** — UI/UX visual design standards.
* **[features/use-cases/chat-immersion.md](features/use-cases/chat-immersion.md)** — UC-001, the core high-immersion chat use case.

## Planning

* **[planning/roadmap.md](planning/roadmap.md)** — exploratory internal roadmap. Read it as working notes on possible direction, not a committed plan; some milestones there (a hosted/multi-tenant deployment path) are explicitly out of scope for the local-first architecture documented above.

## What's not in here

Several first-party documents live directly under `docs/` (outside `en/` and `pt-BR/`) and are intentionally not part of this reference set: superseded audit/improvement-plan write-ups, an internal AI-agent-workflow planning archive (`docs/superpowers/`), and a UI-mockup export (`docs/figma/`). They are development history, not living reference documentation — see the repository's `CHANGELOG.md` for what actually shipped from them. The demo GIF referenced from the root `README.md` lives at `docs/demo/` for both language variants.
