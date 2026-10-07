# Functional Requirements (RF) — Open-ChatBot

> **Legacy scope:** character CRUD, chat history and scenes below describe the
> inherited web/RP application, not the single-SophIA MVP. PE4 requirements are
> in [persona-continuity.md](persona-continuity.md).

## RF-001: Character Persistence
*   **Description**: The system must persist character metadata, personality, and history.
*   **Priority**: P0 (Crucial)
*   **Acceptance Criteria**: Characters can be created, updated, and retrieved with full personality integrity across restarts.

## RF-002: Dynamic Tag System
*   **Description**: Characters must support modular behavioral tags (e.g., "sarcastic", "affectionate").
*   **Priority**: P0
*   **Acceptance Criteria**: Tags are injected into the Master Prompt and demonstrably alter AI response style.

## RF-003: Narrative Sequence Rendering
*   **Description**: The system must output and render structured sequences of Thoughts, Actions, and Speech.
*   **Priority**: P1 (Important)
*   **Acceptance Criteria**: Frontend renders `*italics*` for thoughts, `**bold**` for actions, and standard text for dialogue.

## RF-004: State-to-Behavior Mapping
*   **Description**: Numerical states (Energy, Hunger, Relationship) must influence AI dialogue.
*   **Priority**: P1
*   **Acceptance Criteria**: Character response includes behavioral cues matching low energy or high relationship levels.

## RF-005: User Profile Management
*   **Description**: The system must store and utilize User Name and Gender for character recognition.
*   **Priority**: P1
*   **Acceptance Criteria**: Characters address the user by the defined name and use correct pronouns.

## RF-006: Vector-Based Long-Term Memory
*   **Description**: System must utilize a Vector Store to retrieve relevant past interactions.
*   **Priority**: P2 (Enhancement)
*   **Acceptance Criteria**: AI references events from > 10 messages ago that are relevant to current context.
