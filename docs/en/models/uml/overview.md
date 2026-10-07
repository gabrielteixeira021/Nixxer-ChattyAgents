# UML Diagrams — Open-ChatBot

> **Legacy diagrams:** chats, multiple characters, narrative scenes and
> "Action Completed" below model Open-ChatBot only. They are not the SophIA MVP
> architecture or proof of tool execution; see ADR-007/008.

## 1. Sequence Diagram: AI Response Pipeline
Describes the flow from user input to rendered narrative sequence.

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant A as API Gateway
    participant E as Engine (Character/State)
    participant P as Prompt Builder
    participant L as LLM Service
    participant D as Database

    U->>A: POST /chat (message, character_id)
    A->>D: Fetch Character & User Profile
    D-->>A: Profile Data
    A->>E: Calculate State Modifiers (Energy/Hunger)
    E-->>A: State-Behavior Strings
    A->>P: Assemble Master + Character + Tags + State
    P-->>A: Final Compiled Prompt
    A->>L: Inference Request
    L-->>A: Raw JSON Sequence
    A->>D: Persist Message History
    A->>U: Stream Rendered Sequence (Thought/Action/Speech)
```

## 2. Class Diagram: Core Domain Model
Defines the structural relationships between core entities.

```mermaid
classDiagram
    class User {
        +int id
        +string name
        +string gender
        +list chat_history
    }
    class Character {
        +int id
        +string name
        +string description
        +list tags
        +AgentState current_state
    }
    class Tag {
        +string slug
        +string behavior_modifier
    }
    class AgentState {
        +int energy
        +int hunger
        +int affection
        +to_prompt() string
    }
    class Message {
        +int id
        +datetime timestamp
        +string role
        +list sequence
    }

    User "1" *-- "many" Message
    Character "1" *-- "many" Message
    Character "1" *-- "1" AgentState
    Character "many" o-- "many" Tag
```

## 3. State Machine: Character Engagement
Tracks the emotional and physical state of the character.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Thinking: User Input Received
    Thinking --> Acting: Internal Logic Processed
    Acting --> Speaking: Action Completed
    Speaking --> Idle: Response Delivered
    
    Idle --> Resting: Energy < 20
    Resting --> Idle: Energy > 50 (Periodic Recovery)
```
