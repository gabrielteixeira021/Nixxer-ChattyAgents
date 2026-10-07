# API v1 do SophIA Persona Engine

O contrato canônico está em
[`docs/en/api/persona-v1.openapi.yaml`](../../en/api/persona-v1.openapi.yaml).

## Fronteira atual (API 1.2)

- Endereço padrão: `http://127.0.0.1:8765`.
- `GET /v1/health`: comprova disponibilidade do serviço e do banco local.
- `GET /v1/personas/{character_id}/snapshot`: entrega o `PersonaSnapshot` v1.
- `POST /v1/personas/{character_id}/turn-context`: acrescenta somente memória
  durável relevante e sanitizada.
- `POST /v1/personas/{character_id}/action-context`: acrescenta fatos imutáveis
  de uma ação já validada/executada para realização verbal na personalidade.
- `/v1/memories`: lista, grava, recupera, corrige, confirma, conclui e esquece
  memórias seletivas da identidade contínua.
- Sem autenticação porque o serviço aceita apenas loopback no MVP.
- Sem execução de ferramentas, credenciais, geração de resposta, TTS ou LAN.

Erros não expõem paths, queries ou detalhes internos. Personagem inexistente
retorna `404`; dados incapazes de satisfazer o contrato retornam `422`; banco
indisponível retorna `503`, inclusive durante a construção do snapshot.

`action-context` aceita somente `open_url` e `remember_memory`, com status
`success`, `failed`, `denied` ou `canceled`. Argumentos e detalhes são limitados
e sanitizados; a Persona não pode mudar permissão, target ou resultado.
