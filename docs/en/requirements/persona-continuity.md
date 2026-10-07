# PE4 Requirements — Continuous SophIA Memory

## Glossary

- **Continuous identity:** the single logical SophIA represented by the MVP.
- **Working context:** bounded recent interaction data that may expire.
- **Durable memory:** normalized selected knowledge retained across restarts.
- **Tool intent/result:** typed action request and factual executor response;
  neither is natural-language persona output.

## Functional requirements

### RF-PE4-001 — Resolve one continuous SophIA identity

- **Category:** functional
- **Stakeholder:** Gabriel Teixeira, architect and product owner
- **Priority:** critical
- **Description:** every MVP memory operation resolves one fixed SophIA identity
  and never creates or switches a chat, session, scene or character.
- **Acceptance:** API and domain tests prove two interactions separated by a
  process restart resolve the same identity without `chat_id` or `scene_id`.
- **Assumptions:** the MVP has one local operator and one SophIA.
- **Dependencies:** ADR-007, PersonaSnapshot v1 compatibility adapter.
- **Rationale:** continuity should feel like interaction with one person, not a
  chat application. Multiple characters are a later product feature.
- **Status:** approved
- **Created/updated:** 2026-10-07
- **Version:** 1

### RF-PE4-002 — Persist selected durable memory

- **Category:** functional
- **Stakeholder:** Gabriel Teixeira, architect and product owner
- **Priority:** critical
- **Description:** eligible facts, preferences and commitments can be stored as
  categorized, normalized, revisioned memory with provenance.
- **Eligibility:** explicit "remember" requests persist directly. Inferred facts
  remain candidates until the user confirms them. Credentials, authentication
  tokens, raw transcripts and model replies are never eligible. Sensitive
  personal data requires purpose-specific explicit confirmation. Provenance
  records source type and timestamp but never embeds raw audio, a complete
  transcript or a complete model reply.
- **Retention:** unconfirmed candidates expire after 7 days; completed
  commitments expire after 30 days; preferences and personal facts remain until
  corrected or forgotten. Expiry uses the same complete-removal path as forget,
  including relational rows, vectors, vector metadata, caches and audit
  payloads; at most a content-free tombstone remains. At 1,000 active memories,
  new writes fail clearly and request user review instead of silently deleting
  data.
- **Acceptance:** a stored memory survives restart, is retrieved once after
  deduplication, and follows every eligibility, retention and capacity rule;
  expiry is proven absent from SQL, vectors, metadata, caches and audit payloads
  after restart.
- **Assumptions:** explicit confirmation is available through the voice flow.
- **Dependencies:** RF-PE4-001, RT-PE4-001, LGPD-PE4-001.
- **Rationale:** useful long-term assistance requires recall without retaining
  every utterance.
- **Status:** approved
- **Created/updated:** 2026-10-07
- **Version:** 1

### RF-PE4-003 — Inspect, correct and forget memory

- **Category:** functional
- **Stakeholder:** Gabriel Teixeira, architect and product owner
- **Priority:** critical
- **Description:** the local user can list durable memories, supersede an
  incorrect memory and delete one explicitly.
- **Acceptance:** correction deletes superseded personal content while retaining
  only content-free revision metadata; forget removes all revisions, relational
  rows, vectors, vector metadata, caches and audit payloads, and remains absent
  after restart. At most a content-free tombstone containing memory id, action
  and timestamp may remain.
- **Assumptions:** destructive operations target stable memory identifiers.
- **Dependencies:** RF-PE4-002, LGPD-PE4-001.
- **Rationale:** continuous memory without user control amplifies errors and
  conflicts with access, rectification and erasure rights.
- **Status:** approved
- **Created/updated:** 2026-10-07
- **Version:** 1

## Privacy and technical requirements

### LGPD-PE4-001 — Minimize retained conversation data

- **Category:** privacy/LGPD
- **Stakeholder:** data subject and product owner
- **Priority:** critical
- **Description:** raw audio, full transcripts and full model replies are not
  durable memory by default; only normalized eligible memories are retained.
- **Acceptance:** automated tests complete voice/memory flows with no audio,
  transcript or reply artifact on disk; data inventory names every retained
  memory field and deletion path.
- **Assumptions:** explicit future opt-in may define a separate lawful purpose.
- **Dependencies:** RF-PE4-002, REGLGPD-002 and REGLGPD-003.
- **Rationale:** data minimization reduces privacy exposure and makes forgetting
  practical.
- **Status:** approved
- **Created/updated:** 2026-10-07
- **Version:** 1

### RT-PE4-001 — Bound and sanitize retrieval

- **Category:** technical restriction
- **Stakeholder:** Persona and security maintainers
- **Priority:** critical
- **Description:** retrieval is globally scoped to SophIA, deterministic,
  limited to 8 memories and 1,024 estimated tokens per prompt, deduplicated and
  sanitized against role/policy markers. One normalized memory is limited to
  2,048 UTF-8 bytes.
- **Acceptance:** hostile and oversized memories cannot alter system/tool policy;
  repeated facts appear once; retrieval never exceeds 8 records, 1,024 tokens
  or 2,048 bytes per stored record.
- **Assumptions:** token estimation uses the same tokenizer/budget service as
  prompt assembly.
- **Dependencies:** RF-PE4-002, ADR-008.
- **Rationale:** persisted text is untrusted input and cannot become authority.
- **Status:** approved
- **Created/updated:** 2026-10-07
- **Version:** 1

### RT-PE4-002 — Use an additive reversible migration

- **Category:** technical restriction
- **Stakeholder:** Persona persistence maintainer
- **Priority:** critical
- **Description:** PE4 adds its memory representation without rewriting or
  automatically importing legacy chat, journal or vector data. Rollback is
  operational: disable PE4 reads/writes and leave its schema and data inert.
- **Acceptance:** forward and rollback-mode tests preserve legacy and PE4 data;
  re-enabling PE4 restores the same memories. A down migration is forbidden
  unless export, backup, restore and re-upgrade round trips are proven first.
- **Assumptions:** legacy data remains readable by the legacy application.
- **Dependencies:** RF-PE4-001, RF-PE4-002.
- **Rationale:** additive isolation permits safe rollback and prevents legacy
  roleplay history from contaminating SophIA memory.
- **Status:** approved
- **Created/updated:** 2026-10-07
- **Version:** 1

## Errors and edge cases

- An invalid or empty memory candidate is rejected without persistence.
- Duplicate normalized content updates provenance/revision without retaining
  superseded personal content or creating an unbounded duplicate.
- A database or vector failure is fail-closed and cannot return partial success.
- Concurrent correction/forget uses revision checks; stale updates fail clearly.
- Memory unavailable degrades to a clear memory error, never silent fabricated
  recall.

## Traceability

| Requirement | Decision | Planned realization | Planned proof | Data impact |
|---|---|---|---|---|
| RF-PE4-001 | ADR-007 | Persona identity/application service | singleton + restart tests | identity record/config |
| RF-PE4-002 | ADR-007 | memory domain port + adapters | eligibility/retention/cap/persistence tests | PE4 memory store |
| RF-PE4-003 | ADR-007 | memory management use cases/API | full-erasure/correct/forget restart tests | content-free tombstones |
| LGPD-PE4-001 | ADR-007 | retention policy and adapters | no-artifact + deletion tests | minimized fields |
| RT-PE4-001 | ADR-007/008 | bounded sanitizer/retriever | hostile-input + 8/1,024/2,048 cap tests | sanitized prompt context |
| RT-PE4-002 | ADR-007 | additive migration + feature gate | forward/rollback-mode/re-enable tests | all data preserved |
