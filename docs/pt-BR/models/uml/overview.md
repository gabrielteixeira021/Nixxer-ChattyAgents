# Diagramas UML — Open-ChatBot

> **Diagramas legados:** chats, múltiplos personagens, cenas narrativas e
> "Ação Concluída" abaixo modelam somente o Open-ChatBot. Não representam a
> arquitetura do MVP SophIA nem comprovam execução de ferramenta; consulte
> ADR-007/008.

## 1. Diagrama de Sequência: Pipeline de Resposta da IA
Descreve o fluxo desde a entrada do usuário até a sequência narrativa renderizada.

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

## 2. Diagrama de Classes: Modelo de Domínio Central
Define os relacionamentos estruturais entre as entidades centrais.

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

## 3. Máquina de Estados: Engajamento do Personagem
Rastreia o estado emocional e físico do personagem.

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
