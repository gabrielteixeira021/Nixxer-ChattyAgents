# System Audit Trail

> **Legacy scope:** this audit describes Open-ChatBot chat/inference behavior.
> Narrative actions and model text are not evidence that a SophIA tool ran.
> PE4 memory audit retains no deleted personal content; PE5 tool success is
> recorded only from a structured executor result (ADR-007/008).

To ensure compliance with standard traceability criteria (RN-005), the FastAPI backend maintains a detailed, trace-linked audit log for conversational transactions and inference cycles.

## 1. Inference Correlation ID (`request_id`)
Every call to the `/chat` or `/chat/stream` endpoints triggers the generation of a unique correlation ID (`request_id`) using `uuid.uuid4()`. This ID links all activities in a single generation cycle:

*   **API Logging:** The execution start and final response latency are tagged with this ID.
*   **Database Tracing:** The `MessageNode` table stores the `request_id` for both the user message and the corresponding assistant response variant.
*   **Debug Logs:** Errors, parsing warnings (e.g. failing validation format `RN-003`), and model completion metrics are output with the `request_id` prefix.

Refer to [chat.py](../../../src/backend/api/chat.py) for implementation details.

## 2. Dynamic State Mutation Auditing
Biologically influenced updates (Energy, Hunger, Relationship score) are tracked on each chat interaction. In [chat.py](../../../src/backend/api/chat.py), the helper `parse_actions_to_state()` evaluates the AI narrative response and writes the corresponding state mutation audit entries (e.g., location changes, clothes updates, hunger depletion) directly into the application log.

## 3. Database Integrity & Maintenance
*   **Vacuuming:** Upon startup, the backend automatically triggers `VACUUM` queries to reclaim unused database page allocations and preserve SQLite structural stability. See [database.py](../../../src/backend/db/database.py).
*   **Coverage & Isolation:** Test coverage requires standard mocks to prevent developer changes from directly polluting or modifying the production database (`chatbot.db`).
