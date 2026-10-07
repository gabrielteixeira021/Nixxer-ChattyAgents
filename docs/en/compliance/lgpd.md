# Data Privacy Compliance (GDPR & LGPD)

> The inventory below describes the inherited Open-ChatBot application. The
> SophIA PE4 contract is narrower: durable memory stores normalized selected
> facts, preferences and commitments; raw audio, complete transcripts and full
> model replies are not retained by default. See
> [ADR-007](../architecture/decisions/adr-007.md).

Open-ChatBot is fully offline by default, aligning with the principles of data minimization and privacy-by-design under the Brazilian General Data Protection Law (LGPD) and General Data Protection Regulation (GDPR).

## 1. Data Inventory (Personally Identifiable Information - PII)
The application stores the following local identifiers:
*   **User Profile Data:** Name, gender (stored in SQLite `users` table).
*   **Conversational Data:** Chat messages, thoughts, actions, timestamps, and character diaries (stored in `message_nodes` and `journal_entries` tables).
*   **Embeddings Data:** High-dimensional vector hashes of messages and lore (stored locally in `/chroma_db`).

## 2. LGPD & GDPR Core Compliance Pillars

### A. Principle of Local Sovereignty (Zero Data Sharing)
All PII is persisted in the local SQLite database (`chatbot.db`) and local TurboVec store. No user data is transmitted to cloud APIs or remote servers. All model inference runs on the local CPU/GPU using llama.cpp.

### B. Right to Erasure / Right to be Forgotten (Art. 16 LGPD / Art. 17 GDPR)
Users have full command over their data. 
*   **Database Purging:** Deleting the local database file (`chatbot.db`) and the local vector store directory (`/chroma_db`) immediately and permanently purges all logs.
*   **Chat History Clearing:** Clearing conversations via the UI invokes [clear_chat_history](../../../src/backend/api/chat.py) which explicitly executes SQL `DELETE` queries on `message_nodes` and `journal_entries` for the selected character, resetting state metadata immediately.

### C. Accountability (Art. 37 LGPD)
Actions are locally trace-logged with a `request_id` context to verify the system flows. No telemetry or telemetry logs are leaked outside the system.

### D. SophIA PE4 memory rights

PE4 exposes granular access, correction and forgetting through Persona API 1.1.
The `sophia_memories` table retains only: stable id, fixed identity key,
category, normalized content and its fingerprint, origin/status, provenance
type and timestamp, sensitivity purpose, revision, lifecycle timestamps and
completion/expiry timestamps. It has no chat, session, scene, raw audio,
complete transcript or model-reply field.

Correction overwrites the row and increments its revision; no historical
content revision is retained. Forgetting and expiry physically delete the row.
`sophia_memory_audit` contains only memory id, action, revision and timestamp,
never memory content. PE4 currently creates no vector, vector metadata or cache
representation, so there is no second personal payload to erase. Any future
adapter must join the same full-erasure path before activation.

`SOPHIA_MEMORY_ENABLED=false` is the operational rollback: reads and writes
fail closed while schema and data remain inert. Destructive Alembic downgrade
is intentionally blocked until export, backup, restore and re-upgrade are
proven lossless.
