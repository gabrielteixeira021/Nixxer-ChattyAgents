# Matriz de Rastreabilidade de Requisitos (RTM)

Esta matriz rastreia a relação entre requisitos de engenharia, regras de negócio e sua implementação real no código.

> **Escopo e atualidade:** as seções 1–2 abaixo descrevem capacidades herdadas
> do Open-ChatBot e não são o contrato do MVP SophIA. Os requisitos PE4
> canônicos estão em [persona-continuity.md](persona-continuity.md). Âncoras de
> linha antigas foram removidas porque divergem; links identificam módulos.

## Rastreabilidade planejada da PE4 SophIA

| Requisito | Decisão | Componente planejado | Teste planejado | Estado |
|---|---|---|---|---|
| RF-PE4-001 | ADR-007 | serviço de identidade/aplicação | singleton + restart | Aprovado, não implementado |
| RF-PE4-002 | ADR-007 | porta de memória + adaptadores | persistir/recuperar/deduplicar | Aprovado, não implementado |
| RF-PE4-003 | ADR-007 | API de gestão de memória | listar/corrigir/esquecer + restart | Aprovado, não implementado |
| LGPD-PE4-001 | ADR-007 | política de retenção | sem artefatos brutos + exclusão | Aprovado, não implementado |
| RT-PE4-001 | ADR-007/008 | retriever/sanitizer limitado | input hostil + caps | Aprovado, não implementado |
| RT-PE4-002 | ADR-007 | migração aditiva | forward + rollback | Aprovado, não implementado |

## 1. Requisitos Funcionais (RF)

| ID do Requisito | Descrição | Componente / Módulo | Código / Arquivo de Implementação | Status |
| :--- | :--- | :--- | :--- | :--- |
| **RF-001** | Persistência de Personagem | Schemas de banco de dados & API de Personagem | [models.py](../../../src/backend/db/models.py) (`Character`), [characters.py](../../../src/backend/api/characters.py) (rotas CRUD) | **Implementado** |
| **RF-002** | Sistema Dinâmico de Tags | Entidades Tag no banco & Geração de prompt | [models.py](../../../src/backend/db/models.py) (`Tag`), [bridge.py](../../../src/backend/core/orchestration/bridge.py) (camada `build_prompt`) | **Implementado** |
| **RF-003** | Renderização de Sequência Narrativa | Sequence Parser & renderização HTML | [validator.py](../../../src/backend/core/orchestration/validator.py) (`validate_narrative_formatting`), parser do ChatView no Frontend (formatação CSS de Pensamentos/Ações) | **Implementado** |
| **RF-004** | Mapeamento Estado-para-Comportamento | Atualizador de bio-estado & Modificadores Dinâmicos de Prompt | [state_transitions.py](../../../src/backend/core/engine/state_transitions.py) (`parse_actions_to_state`, `apply_action_stats`), [bridge.py](../../../src/backend/core/orchestration/bridge.py) (camada de estado do `build_prompt`) | **Implementado** |
| **RF-005** | Gerenciamento de Perfil de Usuário | Persistência de usuário no banco & interpolação de prompt | [models.py](../../../src/backend/db/models.py) (`User`), [users.py](../../../src/backend/api/users.py) (rotas), [bridge.py](../../../src/backend/core/orchestration/bridge.py) | **Implementado** |
| **RF-006** | Memória de Longo Prazo Baseada em Vetores | Vector database TurboQuant local | [vector_store.py](../../../src/backend/core/memory/vector_store.py) (`VectorStore`), [bridge.py](../../../src/backend/core/orchestration/bridge.py) (camada de memória/RAG) | **Implementado** |

## 2. Regras de Negócio (RN)

| ID da Regra | Enunciado da Regra | Arquivo / Código de Implementação | Status |
| :--- | :--- | :--- | :--- |
| **RN-001** | Prioridade de Personalidade | [bridge.py](../../../src/backend/core/orchestration/bridge.py) (`build_prompt` carrega `character.description` diretamente como a camada Identity, que sobrepõe as diretrizes globais base dentro da orquestração de template) | **Implementado** |
| **RN-002** | Limiares de Estado-Comportamento | [state_transitions.py](../../../src/backend/core/engine/state_transitions.py) (limiares de delta de stat para os modificadores narrativos de baixa energia/alta fome/alto relacionamento) | **Implementado** |
| **RN-003** | Formatação Obrigatória | [validator.py](../../../src/backend/core/orchestration/validator.py) (exige >= 1 pensamento `*...*` e >= 1 ação `**...**` se a contagem de palavras > 50 palavras) | **Implementado** |
| **RN-004** | Retenção de Memória & Resumo | [bridge.py](../../../src/backend/core/orchestration/bridge.py) (o método `reflect` extrai fatos do usuário e resumo no intervalo de reflexão, resetando o inchaço do histórico local de chat) | **Implementado** |
| **RN-005** | Trilha de Auditoria | [chat.py](../../../src/backend/api/chat.py) (`request_id` gerado via UUID, logado em cada stream de inferência, e salvo no schema `MessageNode`) | **Implementado** |
