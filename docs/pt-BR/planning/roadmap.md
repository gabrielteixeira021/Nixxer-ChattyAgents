# Roadmap de Entrega — Open-ChatBot Enterprise

> **Roadmap legado:** este plano pertence ao produto web/RP herdado. As
> milestones atuais da SophIA são PE4 memória contínua, PE5 ferramentas tipadas
> e PE6 Google Calendar, registradas nas ADR-007/008 e no roadmap do repositório
> pai.

## M01: Núcleo Fundacional (Atual)
*   **Objetivo**: Estabelecer o motor de personagem e a imersão básica de chat.
*   **Entregáveis**:
    *   Schema SQLite + SQLAlchemy.
    *   Lógica de mapeamento Estado-para-Comportamento.
    *   Renderizador de mensagens do frontend (Itálico/Negrito).
*   **Métrica de sucesso**: 100% de aprovação nos testes unitários de consistência de personagem.

## M02: Identidade e Perfil de Usuário
*   **Objetivo**: Reconhecimento de usuário multi-sessão.
*   **Entregáveis**:
    *   CRUD de Perfil de Usuário.
    *   Injeção de Pronome/Nome no Master Prompt.
    *   Recuperação de histórico de chat baseada em sessão.
*   **Métrica de sucesso**: O usuário é chamado pelo nome em > 90% das respostas de início de sessão.

## M03: Memória Avançada (RAG)
*   **Objetivo**: Consciência de contexto de longo prazo.
*   **Entregáveis**:
    *   Integração ChromaDB / FAISS.
    *   Agente automatizado de resumo de "Reflexões".
    *   Lógica de recuperação contextual.
*   **Métrica de sucesso**: A IA referencia um fato do "Reflection Store" em um contexto relevante.

## M04: Escalabilidade e Compliance
*   **Objetivo**: Infraestrutura de nível enterprise.
*   **Entregáveis**:
    *   Migração para PostgreSQL.
    *   Cache Redis para estados de sessão.
    *   Ponte de exclusão de dados LGPD/GDPR.
*   **Métrica de sucesso**: Throughput > 500 req/s com < 200ms de overhead (excluindo inferência).
