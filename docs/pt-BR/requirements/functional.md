# Requisitos Funcionais (RF) — Open-ChatBot

> **Escopo legado:** CRUD de personagens, histórico de chat e cenas abaixo
> descrevem a aplicação web/RP herdada, não o MVP de uma única SophIA. Os
> requisitos PE4 estão em [persona-continuity.md](persona-continuity.md).

## RF-001: Persistência de Personagem
*   **Descrição**: O sistema deve persistir os metadados, a personalidade e o histórico do personagem.
*   **Prioridade**: P0 (Crucial)
*   **Critérios de Aceitação**: Personagens podem ser criados, atualizados e recuperados com integridade total de personalidade entre reinícios.

## RF-002: Sistema Dinâmico de Tags
*   **Descrição**: Os personagens devem suportar tags comportamentais modulares (ex.: "sarcástico", "afetuoso").
*   **Prioridade**: P0
*   **Critérios de Aceitação**: As tags são injetadas no Master Prompt e alteram demonstravelmente o estilo de resposta da IA.

## RF-003: Renderização de Sequência Narrativa
*   **Descrição**: O sistema deve produzir e renderizar sequências estruturadas de Pensamentos, Ações e Fala.
*   **Prioridade**: P1 (Importante)
*   **Critérios de Aceitação**: O frontend renderiza `*itálico*` para pensamentos, `**negrito**` para ações, e texto padrão para diálogo.

## RF-004: Mapeamento Estado-para-Comportamento
*   **Descrição**: Estados numéricos (Energia, Fome, Relacionamento) devem influenciar o diálogo da IA.
*   **Prioridade**: P1
*   **Critérios de Aceitação**: A resposta do personagem inclui indícios comportamentais compatíveis com níveis baixos de energia ou altos de relacionamento.

## RF-005: Gerenciamento de Perfil de Usuário
*   **Descrição**: O sistema deve armazenar e utilizar o Nome e o Gênero do Usuário para reconhecimento de personagem.
*   **Prioridade**: P1
*   **Critérios de Aceitação**: Os personagens se dirigem ao usuário pelo nome definido e usam os pronomes corretos.

## RF-006: Memória de Longo Prazo Baseada em Vetores
*   **Descrição**: O sistema deve utilizar um Vector Store para recuperar interações passadas relevantes.
*   **Prioridade**: P2 (Melhoria)
*   **Critérios de Aceitação**: A IA referencia eventos de mais de 10 mensagens atrás que sejam relevantes para o contexto atual.
