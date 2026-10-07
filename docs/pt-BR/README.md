# Documentação do Open-ChatBot

Documentação de referência sobre a arquitetura, modelo de dados, testes, requisitos e postura de compliance do Open-ChatBot. Esta árvore espelha [docs/en/](../en/) arquivo por arquivo; se um link aqui der 404 na árvore em inglês, é porque aquela página ainda não foi traduzida.

## Comece por aqui

* **[setup/quickstart.md](setup/quickstart.md)** — pré-requisitos e passos de execução, consolidados a partir do README e dos scripts de execução.
* **[architecture.md](architecture.md)** — o fluxo turno a turno, o ciclo de memória/reflexão e o pipeline de montagem do prompt. O documento de arquitetura mais detalhado deste repositório; leia primeiro para entender como um turno de chat realmente funciona.
* **[data-model-er.md](data-model-er.md)** — o schema relacional mais o vector store de memória fora da banda, e as decisões não óbvias por trás deles (o "espelho" Chat↔AgentState, persona por chat, histórico soft-delete-only).
* **[testing.md](testing.md)** — como rodar as suítes de teste, garantias de isolamento, e como adicionar uma feature sem quebrar nenhuma das duas.
* **[card-authoring-epic.md](card-authoring-epic.md)** — como escrever uma card de personagem que faz um modelo local pequeno performar bem.

## Requisitos

* **[requirements/ers.md](requirements/ers.md)** — Especificação de Requisitos de Engenharia (ERS).
* **[requirements/functional.md](requirements/functional.md)** — requisitos funcionais (RF-xxx).
* **[requirements/non-functional.md](requirements/non-functional.md)** — metas não funcionais (RNF-xxx); leia a entrada de Disponibilidade antes de citar qualquer número de uptime deste repositório.
* **[requirements/business-rules.md](requirements/business-rules.md)** — regras de negócio (RN-xxx).
* **[requirements/traceability-matrix.md](requirements/traceability-matrix.md)** — matriz de rastreabilidade requisito-implementação.

## Arquitetura

* **[architecture/overview.md](architecture/overview.md)** — drivers de sistema de alto nível e lista de componentes, em um grão mais grosso que `architecture.md` acima. Os dois documentos foram escritos em momentos e profundidades diferentes; `architecture.md` é o que deve ser considerado confiável para como o pipeline de prompt e o ciclo de memória se comportam hoje; este aqui serve como orientação de uma página só.
* **[architecture/decisions/](architecture/decisions/)** — Architecture Decision Records (ADR-002 banco de dados/persistência, ADR-003 inferência local-first, ADR-004 linguagem/orquestração, ADR-005 fronteira do SophIA Persona Engine, ADR-006 API local dedicada de Persona).
* **[architecture/c4/](architecture/c4/)** — notas de contexto/container/componente no modelo C4 e a fonte do diagrama.
* **[architecture/security.md](architecture/security.md)** — modelo de ameaças STRIDE para a implantação single-tenant, somente local.

## Modelos

* **[models/domain-boundaries.md](models/domain-boundaries.md)** — bounded contexts de DDD e a fonte do diagrama de classes de domínio.
* **[models/uml/overview.md](models/uml/overview.md)** — diagramas de sequência/classe/estado.
* **[models/erd/README.md](models/erd/README.md)** — detalhe de ERD em nível de tabela, uma visão complementar a `data-model-er.md` acima.

## API

* **[api/openapi.yaml](../en/api/openapi.yaml)** — o contrato OpenAPI. Neutro em relação a idioma; não duplicado na árvore em português.
* **[api/persona-v1.md](api/persona-v1.md)** — guia da API versionada e restrita a loopback do SophIA Persona Engine.
* **[api/auth.md](api/auth.md)** — modelo de autenticação atual (não existe um — single-tenant, vinculado a loopback, sem middleware) e o que uma implantação em produção/multi-tenant exigiria.

## Infraestrutura e compliance

* **[infrastructure/ci-cd.md](infrastructure/ci-cd.md)** — os gates reais de CI (`.github/workflows/qa.yml`, `.github/workflows/e2e.yml`).
* **[infrastructure/sre.md](infrastructure/sre.md)** — gerenciamento de processos locais, health checks e manutenção de armazenamento.
* **[compliance/lgpd.md](compliance/lgpd.md)** — postura de privacidade de dados LGPD/GDPR para uma aplicação totalmente local e offline por padrão.
* **[compliance/audit.md](compliance/audit.md)** — a trilha de auditoria por ID de correlação de requisição.

## Design e features

* **[design/immersion-guidelines.md](design/immersion-guidelines.md)** — padrões de design visual de UI/UX.
* **[features/use-cases/chat-immersion.md](features/use-cases/chat-immersion.md)** — UC-001, o caso de uso central de chat de alta imersão.

## Planejamento

* **[planning/roadmap.md](planning/roadmap.md)** — roadmap interno exploratório. Leia como notas de trabalho sobre uma direção possível, não como um plano comprometido; alguns marcos ali (um caminho de implantação hospedada/multi-tenant) estão explicitamente fora do escopo da arquitetura local-first documentada acima.

## O que não está aqui

Vários documentos internos ficam diretamente em `docs/` (fora de `en/` e `pt-BR/`) e ficam deliberadamente fora deste conjunto de referência: relatórios de auditoria/planos de melhoria superados, um arquivo interno de planejamento de workflow de agente de IA (`docs/superpowers/`), e uma exportação de mockup de UI (`docs/figma/`). São histórico de desenvolvimento, não documentação de referência viva — veja o `CHANGELOG.md` do repositório para o que de fato foi entregue a partir deles. O GIF de demonstração referenciado no `README.md` da raiz vive em `docs/demo/` para as duas variantes de idioma.
