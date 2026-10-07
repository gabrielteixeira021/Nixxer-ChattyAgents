# Requisitos Não Funcionais (RNF) — Open-ChatBot

> **Escopo legado:** estas metas pertencem ao Open-ChatBot. Qualidade,
> privacidade e rollback da PE4 SophIA são canônicos em
> [persona-continuity.md](persona-continuity.md).

## RNF-001: Disponibilidade
*   **Status**: Nenhuma meta de uptime é rastreada ou mensurável hoje. Esta é uma aplicação local-first, single-user, sem instância implantada/hospedada e sem infraestrutura de monitoramento ou SLA no repositório — um número de uptime (ex.: "99,9%") seria inverificável e não é afirmado aqui.
*   **Aspiração**: Caso o projeto algum dia migre para uma implantação hospedada/multi-tenant, definir uma meta de disponibilidade nesse momento, apoiada em monitoramento real.
*   **Restrição (atual, verificável)**: O backend deve degradar graciosamente quando o subprocesso local `llama-server` estiver inalcançável, em vez de derrubar o processo da API.

## RNF-002: Performance (Latência)
*   **Meta**: Resposta da API (TTFB) < 500ms; Inferência completa < 3000ms.
*   **Restrição**: Usar processamento assíncrono para atualizações de UI não bloqueantes.

## RNF-003: Escalabilidade
*   **Meta**: Suportar até 10 mil sessões concorrentes por nó (pronto para escalonamento horizontal).
*   **Restrição**: Camada de API stateless; store de sessão externo (Redis) para escalonamento.

## RNF-004: Segurança (Dados em Repouso)
*   **Meta**: Criptografia AES-256 para dados sensíveis de perfil de usuário.
*   **Restrição**: Nenhum log de PII bruta ou chat bruto do usuário em logs de produção.

## RNF-005: Observabilidade
*   **Meta**: Tracing distribuído completo (OpenTelemetry) para o pipeline de inferência.
*   **Restrição**: Logging centralizado com JSON estruturado (compatível com ELK/Grafana).

## RNF-006: Compliance
*   **Meta**: Compliance total com GDPR/LGPD (Direito ao Apagamento / Portabilidade de Dados).
*   **Restrição**: "Ponte de Privacidade" modular para lidar com solicitações de exclusão de dados.

## RNF-007: Testabilidade (Zero Contato com Produção)
*   **Meta**: 100% dos testes funcionais rodam em ambientes efêmeros e isolados.
*   **Restrição**: Aplicação estrita de `TEST_DB` e `PROD_DB` separados.
