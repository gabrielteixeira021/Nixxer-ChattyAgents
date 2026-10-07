# API v1 do SophIA Persona Engine

O contrato canônico está em
[`docs/en/api/persona-v1.openapi.yaml`](../../en/api/persona-v1.openapi.yaml).

## Fronteira da PE2

- Endereço padrão: `http://127.0.0.1:8765`.
- `GET /v1/health`: comprova disponibilidade do serviço e do banco local.
- `GET /v1/personas/{character_id}/snapshot`: entrega o `PersonaSnapshot` v1.
- Sem autenticação porque o serviço aceita apenas loopback no MVP.
- Sem geração de resposta, RAG, mutação de estado, TTS ou acesso por LAN.

Erros não expõem paths, queries ou detalhes internos. Personagem inexistente
retorna `404`; dados incapazes de satisfazer o contrato retornam `422`; banco
indisponível retorna `503`.
