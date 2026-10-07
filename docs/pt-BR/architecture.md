# Arquitetura

Open-ChatBot é um motor de personagem/RP com estado, local, self-hosted e single-user.
Backend FastAPI + SQLAlchemy + SQLite, frontend React + TS + Vite, e um
`llama-server` (llama.cpp) local fornecendo inferência e embeddings. Este documento
descreve os fluxos que atravessam muitos arquivos; para o schema veja
[data-model-er.md](./data-model-er.md).

## Composition root

Os singletons de escopo de aplicação `llama_client`, `vector_store`, `brain` são
construídos uma única vez em `core/deps.py` e importados em todo lugar. Nunca
construa sua própria instância — instâncias separadas significam vector stores em
memória divergentes sobre o mesmo caminho em disco, então uma memória adicionada
por uma delas fica invisível para a outra até o restart.

A API Persona da SophIA possui um composition root mínimo e separado:
`core/persona/deps.py` mantém seu singleton de domínio e `persona_main.py`
inicializa um serviço FastAPI restrito a loopback, com persistência, mas sem
runtime de LLM, RAG, frontend ou voz. Essa fronteira não altera o fluxo da
aplicação de chat legada. Consulte a
[ADR-006](architecture/decisions/adr-006.md).

## O turno de chat

```mermaid
sequenceDiagram
    participant C as Client
    participant API as api/chat.py
    participant Brain as Brain.build_prompt
    participant LL as llama-server
    participant BG as run_consciousness_layer (bg)
    C->>API: POST /chat ou /chat/stream
    API->>API: _prepare_chat_turn: resolve user/character/state/chat
    API->>API: need-decay (somente dynamic) + action deltas; valida parent_id
    API->>API: persiste mensagem do usuário; percorre o histórico da branch ativa
    API->>Brain: build_prompt(state, history, lore, memory, budget)
    Brain->>LL: query_memory (RAG) + tokenize (budget)
    API->>LL: complete / complete_stream
    LL-->>API: reply
    API->>API: parse_actions_to_state; _persist_assistant_reply (retry em StaleData)
    API->>BG: agenda run_consciousness_layer
    BG->>LL: armazena memória; extract_scene (todo turno); no intervalo, reflect + evolve
```

`_prepare_chat_turn` é compartilhado por `POST /chat` e `POST /chat/stream` para que
os dois caminhos não possam divergir. A reflexão é baseada em checkpoint:
`force_reflect = interaction_count - last_reflected_at_count >= REFLECTION_INTERVAL`
(uma reflexão de boundary que falhou é reprocessada, nunca pulada para sempre).

**Rastreamento de cena por turno.** Depois de cada turno, `run_consciousness_layer`
roda um extrator de cena barato — `Brain.extract_scene` (uma GBNF `SCENE_GRAMMAR`
minúscula sobre apenas a última resposta → `{location, mood}`) seguido de
`engine.apply_scene_update` (ciente do espelho, com o mesmo padrão
`with_for_update` + retry em `StaleDataError` de `evolve_character`). Isso é
**desacoplado** da reflexão de 20 turnos, de modo que um movimento como *"pega o
elevador para descer"* atualiza o HUD e a âncora de recência imediatamente, em vez
de só na próxima fronteira de reflexão. É pulado sob pytest (assim como o boot do
llama) e qualquer falha é não-fatal — o turno já foi concluído com sucesso.

**Persona dinâmica vs. estática.** `Character.dynamic_persona` (booleano, padrão
`True`) controla a simulação em `_prepare_chat_turn`. Dinâmico (padrão) roda
need-decay e evolução guiada por reflexão; estático congela a persona exatamente
como foi escrita (sem decay, sem deriva) — `force_reflect` e `update_needs` são
ambos suprimidos. O rastreamento de cena e a recuperação de memória rodam em
**ambos** os modos; apenas a simulação que muta a persona é controlada por essa
flag. Uma linha legada com a flag `NULL` assume o padrão dinâmico.

## Estado em duas camadas (o espelho)

Um personagem tem um `AgentState` contendo a persona **ao vivo**; cada `Chat` é uma
história separada e o armazenamento **canônico** dos seus campos locais à conversa
+ o snapshot da persona. `AgentState` espelha o chat ativo; trocar de chat salva o
snapshot que está saindo e restaura o que está entrando. A persona é **por chat**
(B8): histórias independentes. Veja [data-model-er.md](./data-model-er.md) §2.

## Ciclo de vida da memória (anti-poison)

- **Escopo:** toda memória, percurso de histórico e journal é escopado por
  `(character_id, chat_id)`, de forma que um chat nunca pode contaminar outro.
- **Armazenamento:** as memórias RAG vivem em um store turbovec em disco (não no
  banco relacional), ligadas às mensagens apenas pelo metadado `message_id`.
  Purgadas manualmente em edit/delete/regenerate.
- **Recuperação (`query_memory`):** over-fetch → gate por limiar de relevância →
  re-ranking combinado de cosseno+recência → dedup de quase-duplicatas → descarta
  memórias já visíveis no histórico recente. Os resultados montados no prompt são
  sanitizados contra injeção de marcador de role e limitados em tamanho.
- **Limitação:** quando um escopo de chat excede o teto, as memórias mais antigas
  são condensadas pelo LLM em uma memória consolidada única (grava antes de
  apagar).
- **Durabilidade:** `_atomic_dump` grava em um diretório temporário e depois troca,
  de modo que um crash não pode deixar o store corrompido pela metade.

## Montagem do prompt (`core/orchestration/bridge.py`)

Um prompt em camadas ultra-compacto para modelos locais pequenos, com orçamento de
tokens definido por `core/context/budget.py` (tetos fixos por camada + um piso de
histórico). `Brain.build_prompt` preenche o `ENTITY_PROMPT_TEMPLATE` nesta ordem:
master prompt → identidade/persona/cenário/tags → persona do usuário → estado
comprimido → memória RAG + lorebook (chaves regex com word boundaries, scan_depth,
chaves secundárias, cooldown) → `active_summary` rolante → diálogos de exemplo →
histórico → a última mensagem do usuário → **âncora de recência** → `Reply:`. Todo
campo de card/persona em texto livre é sanitizado e limitado em tamanho.

**Master prompt (mecânica de engajamento E.P.I.C.).** `COMPRESSED_MASTER_PROMPT`
(`core/context/compressor.py`) é escrito em torno de engajamento, não de contagem
de palavras: manter a voz/tiques exatos do personagem, reagir e construir sobre a
última entrada do usuário, impulsionar e escalar um desejo/tensão visível a cada
turno, ancorar um beat sensorial que *age sobre* o usuário, e terminar com um
gancho que convida uma resposta curta — com comprimento adaptativo casado com a
energia do usuário. A antiga regra de comprimento forçado "living entity / 3-5
parágrafos / não apresse" não existe mais.

**Âncora de persona em posição dupla.** `Brain._build_anchor` reinjeta um bloco
compacto "Você é {name}. {persona-essence}. Agora: {location}; humor {mood}.
Responda na voz; reaja; conduza a tensão; termine com um gancho." bem **antes de
`Reply:`**, de modo que a persona fique em **ambas as pontas** do prompt (primazia
no topo + recência no fim). Um modelo de ~4B presta atenção no início e no fim e
perde o meio de uma janela longa, então a cena e a voz atuais são a última coisa
que ele lê antes de gerar. A âncora é derivada dos campos já existentes na card
(sem novo schema) e limitada por `settings.ANCHOR_TOKENS`.

**A sanitização preserva quebras de linha.** `_sanitize` mantém a estrutura de
linhas (normalizando apenas os finais de linha e limitando sequências de linhas em
branco), de modo que os cabeçalhos de seção e listas com marcadores de uma card —
uma alavanca real de caracterização em modelos pequenos — sobrevivam em vez de
serem achatados. A remoção do dois-pontos após qualquer marcador de role (incl. o
nome do usuário/personagem ao vivo) é o que efetivamente bloqueia a forja de turno
/ um `Reply:` prematuro (A2).

**Tetos de card.** Os campos de texto livre da card (persona/cenário/descrição/
exemplos) não são mais cortados em 300 tokens — aquela guilhotina cortava personas
reais para ~225 palavras e era uma das principais causas de "o personagem parece
genérico". Agora são limitados pelo generoso `settings.CARD_MAX_TOKENS` (8000) via
`_truncate_at_sentence` (corta em um limite de frase, nunca no meio de uma
palavra, e só dispara em um campo patologicamente longo).
`settings.RECOMMENDED_CARD_TOKENS` (4096) é apenas uma sugestão suave de UI.

**Janela de histórico.** Mesmo em um contexto grande (`models_config.json` agora
tem `context_size` padrão de 49152 / 48k, subindo de 4096), o histórico bruto é
limitado a `settings.HISTORY_WINDOW_TOKENS` (10000) em `budget.py` — alimentar
~40k de turnos brutos enterra a persona/âncora na zona de "perdido no meio".
Turnos mais antigos que a janela são carregados pelo resumo rolante + RAG, não
despejados brutos.

**Estado comprimido (`compress_state`).** O relacionamento é expresso como um
**dial** de calor renderizado "com voz própria" (frio / reservado / caloroso /
próximo + score), substituindo o antigo rótulo genérico
`Rel(Acquaintance): Polite but reserved` que homogeneizava todo personagem em um
único tom. Os modificadores fisiológicos são bidirecionais: energia ≥ 80 agora é
lida como `ENERGIZED` (alerta/animado), não apenas os avisos de exaustão por baixa
energia.

## Reflexão / evolução (`core/engine/engine.py`)

`run_consciousness_layer` (tarefa em background) armazena a memória do turno, roda
o extrator de cena por turno (acima) e — apenas no intervalo e apenas para um
personagem `dynamic_persona` — chama `brain.reflect` (JSON restrito por GBNF) e
depois `evolve_character`. A evolução aplica a reflexão (delta de relacionamento,
fatos, traços, camadas de calor de tag, resumo rolante, journal, localização/humor)
dentro de uma transação com `with_for_update` + guarda de versão, com retries em
`StaleDataError`. Se o usuário trocou de chat durante o `reflect()` lento, a
reflexão é aplicada ao snapshot do chat que *estava refletindo*, nunca ao que está
ativo agora. `apply_scene_update` segue o mesmo padrão ciente do espelho para sua
escrita mais leve, de localização/humor apenas.

## Runner do llama-server (`core/engine/runner.py`)

Sobe automaticamente um llama-server local consolidado (inferência + embeddings em
uma única porta, padrão 8080) a partir de `models_config.json` na inicialização,
com verificação de saúde via polling de warmup. Completamente ignorado sob
pytest/E2E.

## Serving

`main.py` registra os routers (chat, characters, tags, users, settings, lore,
presets) e monta o frontend já compilado a partir de `static/` com um catch-all de
SPA — as rotas de API são registradas antes do catch-all.
