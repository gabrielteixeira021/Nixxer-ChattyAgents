# Security Architecture

Open-ChatBot implements a "Privacy-by-Design" architecture model optimized for local, offline execution.

## 1. Threat Modeling (STRIDE Analysis)
*   **Spoofing:** Risk is mitigated by running as a single-user local service.
*   **Tampering:** Local SQLite database file (`chatbot.db`) is protected by operating system user filesystem access control permissions.
*   **Repudiation:** Checked via application-level audit logging. All inference requests write audit traces containing unique UUID `request_id` values.
*   **Information Disclosure:** Risk is extremely low because data never traverses external networks. No cloud-based LLM APIs are used (all generation goes through a local loopback `llama-server.exe` instance).
*   **Denial of Service:** The inference loop blocks local compute resources. To prevent resource exhaustion, the execution processes are restricted to the local device's memory limitations.
*   **Elevation of Privilege:** The backend process executes under the security context of the user launching the `run.bat` script.

## 2. Authentication & Authorization
Currently, there is no session authentication (JWT/OAuth) in the API layer because the system operates in a single-tenant local environment (binding to localhost loopback `127.0.0.1`). If deployment to external networks is required, authentication must be added to the FastAPI layer. Refer to [auth.md](../api/auth.md) for recommendation guidelines.

## 3. Data Protection
*   **ORM Protection:** Database interactions are mediated by SQLAlchemy ORM schemas, preventing SQL injection vulnerabilities.
*   **Vector Database Security:** Local vector databases reside inside `./chroma_db/` using standard binary files without network exposure.
*   **Safety Limits:** Inference limits are constrained by local `models_config.json` parameter allocations.
*   **Sanitization:** Persona and memory text are untrusted inputs and are
    sanitized before prompt assembly. Prompt instructions are not a command
    security boundary.
*   **Tool boundary:** Persona Engine owns no credentials, permission decisions
    or executors. Future tools accept typed allowlisted intents in the SophIA
    agent core, and natural-language model output is never executed directly.
    See [ADR-008](decisions/adr-008.md).
