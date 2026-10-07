# Requirements Traceability Matrix (RTM)

This matrix tracks the relationship between engineering requirements, business rules, and their actual implementation in the codebase.

> **Scope and currency:** sections 1–2 below describe inherited Open-ChatBot
> capabilities and are not the SophIA MVP contract. PE4 requirements are
> canonical in [persona-continuity.md](persona-continuity.md). Older line-number
> anchors were removed because they drift; file links identify modules only.

## SophIA PE4 planned traceability

| Requirement | Decision | Planned component | Planned test | Status |
|---|---|---|---|---|
| RF-PE4-001 | ADR-007 | Persona identity/application service | singleton + restart | Approved, not implemented |
| RF-PE4-002 | ADR-007 | memory domain port + adapters | persist/retrieve/dedup | Approved, not implemented |
| RF-PE4-003 | ADR-007 | memory management API | list/correct/forget + restart | Approved, not implemented |
| LGPD-PE4-001 | ADR-007 | retention policy | no raw artifacts + deletion | Approved, not implemented |
| RT-PE4-001 | ADR-007/008 | bounded sanitizer/retriever | hostile input + caps | Approved, not implemented |
| RT-PE4-002 | ADR-007 | additive migration | forward + rollback | Approved, not implemented |

## 1. Functional Requirements (RF)

| Requirement ID | Description | Component / Module | Implementation Code / File | Status |
| :--- | :--- | :--- | :--- | :--- |
| **RF-001** | Character Persistence | Database schemas & Character API | [models.py](../../../src/backend/db/models.py) (`Character`), [characters.py](../../../src/backend/api/characters.py) (CRUD routes) | **Implemented** |
| **RF-002** | Dynamic Tag System | DB Tag entities & Prompt generation | [models.py](../../../src/backend/db/models.py) (`Tag`), [bridge.py](../../../src/backend/core/orchestration/bridge.py) (`build_prompt` layer) | **Implemented** |
| **RF-003** | Narrative Sequence Rendering | Sequence Parser & HTML rendering | [validator.py](../../../src/backend/core/orchestration/validator.py), Frontend ChatView parser (CSS formatting of Thoughts/Actions) | **Implemented** |
| **RF-004** | State-to-Behavior Mapping | Bio-state updater & Dynamic Prompt Modifiers | [state_transitions.py](../../../src/backend/core/engine/state_transitions.py) (`parse_actions_to_state`, `apply_action_stats`), [bridge.py](../../../src/backend/core/orchestration/bridge.py) (`build_prompt` state layer) | **Implemented** |
| **RF-005** | User Profile Management | User database persistence & prompt interpolation | [models.py](../../../src/backend/db/models.py) (`User`), [users.py](../../../src/backend/api/users.py) (routes), [bridge.py](../../../src/backend/core/orchestration/bridge.py) | **Implemented** |
| **RF-006** | Vector-Based Long-Term Memory | Local TurboQuant Vector database | [vector_store.py](../../../src/backend/core/memory/vector_store.py) (`VectorStore`), [bridge.py](../../../src/backend/core/orchestration/bridge.py) (memory/RAG layer) | **Implemented** |

## 2. Business Rules (RN)

| Rule ID | Rule Statement | Implementation File / Code | Status |
| :--- | :--- | :--- | :--- |
| **RN-001** | Personality Priority | [bridge.py](../../../src/backend/core/orchestration/bridge.py) (`build_prompt` loads `character.description` directly as the Identity layer, which overrides global base guidelines inside template orchestration) | **Implemented** |
| **RN-002** | State-Behavior Thresholds | [state_transitions.py](../../../src/backend/core/engine/state_transitions.py) (stat-delta thresholds for the low-energy/high-hunger/high-relationship narrative modifiers) | **Implemented** |
| **RN-003** | Formatting Enforced | [validator.py](../../../src/backend/core/orchestration/validator.py) (requires >= 1 thought `*...*` and >= 1 action `**...**` if word count > 50 words) | **Implemented** |
| **RN-004** | Memory Retention & Summary | [bridge.py](../../../src/backend/core/orchestration/bridge.py) (`reflect` method parses user facts and summary on the reflection interval, resetting local chat history bloat) | **Implemented** |
| **RN-005** | Audit Trail | [chat.py](../../../src/backend/api/chat.py) (`request_id` generated via UUID, logged with every inference stream, and saved in the `MessageNode` schema) | **Implemented** |
