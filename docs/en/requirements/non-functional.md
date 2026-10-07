# Non-Functional Requirements (RNF) — Open-ChatBot

> **Legacy scope:** these targets belong to Open-ChatBot. SophIA PE4 quality,
> privacy and rollback requirements are canonical in
> [persona-continuity.md](persona-continuity.md).

## RNF-001: Availability
*   **Status**: No uptime target is tracked or measurable today. This is a local-first, single-user application with no deployed/hosted instance and no monitoring or SLA infrastructure in the repository — a numeric uptime figure (e.g. "99.9%") would be unverifiable and is not asserted.
*   **Aspiration**: Should the project ever move to a hosted/multi-tenant deployment, define an availability target then, backed by real monitoring.
*   **Constraint (current, verifiable)**: The backend should degrade gracefully when the local `llama-server` subprocess is unreachable, rather than crash the API process.

## RNF-002: Performance (Latency)
*   **Target**: API response (TTFB) < 500ms; Full inference < 3000ms.
*   **Constraint**: Use asynchronous processing for non-blocking UI updates.

## RNF-003: Scalability
*   **Target**: Support up to 10k concurrent sessions per node (horizontal scaling ready).
*   **Constraint**: Stateless API tier; external session store (Redis) for scaling.

## RNF-004: Security (Data-at-Rest)
*   **Target**: AES-256 encryption for sensitive user profile data.
*   **Constraint**: No logging of raw PII or raw user chat in production logs.

## RNF-005: Observability
*   **Target**: Full distributed tracing (OpenTelemetry) for inference pipeline.
*   **Constraint**: Centralized logging with structured JSON (ELK/Grafana compatible).

## RNF-006: Compliance
*   **Target**: Full GDPR/LGPD compliance (Right to Erasure / Data Portability).
*   **Constraint**: Modular "Privacy Bridge" to handle data deletion requests.

## RNF-007: Testability (Zero-Production Contact)
*   **Target**: 100% of functional tests run in ephemeral, isolated environments.
*   **Constraint**: Strict enforcement of separate `TEST_DB` and `PROD_DB`.
