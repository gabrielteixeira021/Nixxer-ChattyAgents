# Bounded Contexts

> **Legacy scope:** this model describes Open-ChatBot. The SophIA MVP has one
> continuous identity and selective memory (ADR-007); its agent core, not
> Persona Engine, owns tool authority (ADR-008).

Domain-driven design boundaries defining the core concepts of Open-ChatBot.

## Core Domains

### User Context
Represents the human player interacting with the system.
- **Models**: `User`

### Character Context
Contains the definition, state, and behavioral rules of an AI persona.
- **Models**: `Character`, `Tag`, `AgentState`
- **Key Concepts**: Personas, dynamic stats (energy, mood, location), behavioral tags.

### Chat & Memory Context
Handles the interactions, long-term memory, and world-building facts.
- **Models**: `MessageNode`, `LorebookEntry`, `JournalEntry`
- **Key Concepts**: Conversation branching (message nodes), event summarization (journal), and RAG-injected facts (lorebook).

## Domain Diagram

The structural relationship of these boundaries is documented in the Class Diagram below.

![Domain Class Diagram](./cl_domain_chatbot.puml)
