# Bounded Contexts

> **Escopo legado:** este modelo descreve o Open-ChatBot. O MVP SophIA possui
> uma identidade contínua e memória seletiva (ADR-007); o núcleo agente, não o
> Persona Engine, possui autoridade sobre ferramentas (ADR-008).

Fronteiras de domain-driven design definindo os conceitos centrais do Open-ChatBot.

## Domínios Centrais

### Contexto de Usuário
Representa o jogador humano interagindo com o sistema.
- **Models**: `User`

### Contexto de Personagem
Contém a definição, o estado e as regras comportamentais de uma persona de IA.
- **Models**: `Character`, `Tag`, `AgentState`
- **Conceitos-chave**: Personas, stats dinâmicos (energia, humor, localização), tags comportamentais.

### Contexto de Chat & Memória
Lida com as interações, memória de longo prazo e fatos de construção de mundo.
- **Models**: `MessageNode`, `LorebookEntry`, `JournalEntry`
- **Conceitos-chave**: Ramificação de conversa (message nodes), sumarização de eventos (journal), e fatos injetados via RAG (lorebook).

## Diagrama de Domínio

O relacionamento estrutural dessas fronteiras está documentado no Diagrama de Classes abaixo.

![Diagrama de Classes de Domínio](../../en/models/cl_domain_chatbot.puml)
