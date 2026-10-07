# Requisitos PE4 — Memória contínua da SophIA

## Glossário

- **Identidade contínua:** a única SophIA lógica representada pelo MVP.
- **Contexto de trabalho:** interação recente limitada que pode expirar.
- **Memória durável:** conhecimento normalizado e selecionado entre interações.
- **Intenção/resultado de ferramenta:** pedido tipado e resposta factual do
  executor; não são narrativa gerada pela persona.

## Requisitos aprovados

| ID | Categoria | Prioridade | Descrição | Aceite mensurável | Dependências |
|---|---|---|---|---|---|
| RF-PE4-001 | Funcional | Crítica | Resolver uma única identidade SophIA, sem criar/trocar chat, sessão, cena ou personagem | Duas interações separadas por restart resolvem a mesma identidade sem `chat_id`/`scene_id` | ADR-007, compatibilidade PersonaSnapshot v1 |
| RF-PE4-002 | Funcional | Crítica | Persistir fatos, preferências e compromissos elegíveis com categoria, normalização, revisão e proveniência sem conteúdo bruto | Pedido explícito persiste; inferência exige confirmação; candidato expira em 7 dias, compromisso concluído em 30; fatos/preferências ficam até correção/esquecimento; expiração apaga SQL/vetor/metadata/cache/auditoria e deixa no máximo tombstone sem conteúdo; limite de 1.000 ativos | RF-PE4-001, RT-PE4-001, LGPD-PE4-001 |
| RF-PE4-003 | Funcional | Crítica | Listar, corrigir e esquecer memória durável | Correção apaga conteúdo substituído; forget remove revisões, SQL, vetor, metadata, cache e payload de auditoria após restart, restando no máximo tombstone sem conteúdo | RF-PE4-002, LGPD-PE4-001 |
| LGPD-PE4-001 | Privacidade | Crítica | Não reter áudio, transcrição completa ou resposta completa por padrão | Fluxos automatizados terminam sem esses artefatos no disco e inventário documenta campos retidos | RF-PE4-002, REGLGPD-002/003 |
| RT-PE4-001 | Restrição técnica | Crítica | Recuperação global, determinística, limitada a 8 memórias/1.024 tokens e 2.048 bytes por registro, deduplicada e sanitizada | Memória hostil não altera papéis/política; duplicata aparece uma vez; todos os caps são respeitados | RF-PE4-002, ADR-008 |
| RT-PE4-002 | Restrição técnica | Crítica | Migração aditiva sem backfill; rollback desliga leitura/escrita e mantém schema/dados PE4 inertes | Forward, rollback-mode e reativação preservam dados; down migration só após export/backup/restore/re-upgrade comprovados | RF-PE4-001/002 |

**Stakeholder originário:** Gabriel Teixeira, arquiteto e product owner.
**Status:** aprovado. **Criação/alteração:** 2026-10-07. **Versão:** 1.

## Rationale

Uma assistente contínua precisa recordar fatos úteis sem se comportar como uma
aplicação de chats nem armazenar indiscriminadamente a fala do usuário. Controle
granular reduz dano de memórias incorretas e atende acesso, retificação e
exclusão. A migração aditiva preserva rollback e impede contaminação por
histórico de roleplay legado.

Somente as categorias `preference`, `personal_fact` e `commitment` entram na
PE4. Credenciais, tokens, áudio, transcrições e respostas completas são
inelegíveis. Dado sensível exige confirmação explícita ligada à finalidade.
Proveniência registra tipo da fonte e timestamp, nunca áudio bruto, transcrição
completa ou resposta completa. Expiração usa o mesmo caminho de apagamento
total do esquecimento e é comprovada após restart. Estado durável de tarefas
fica fora da PE4 e não é implícito na PE5; exige contrato futuro próprio.

## Erros e casos limite

- Candidato vazio ou inválido é rejeitado sem persistência.
- Duplicata atualiza proveniência/revisão sem reter conteúdo pessoal substituído
  nem crescer indefinidamente.
- Falha SQL ou vetorial é fail-closed e não retorna sucesso parcial.
- Correção/esquecimento concorrente usa revisão; escrita obsoleta falha.
- Memória indisponível gera erro explícito, nunca recordação inventada.

## Rastreabilidade

| Requisito | Decisão | Realização planejada | Prova planejada | Impacto de dados |
|---|---|---|---|---|
| RF-PE4-001 | ADR-007 | serviço de identidade/aplicação | testes singleton + restart | identidade/configuração |
| RF-PE4-002 | ADR-007 | porta de memória + adaptadores | elegibilidade/retenção/caps/persistência | store PE4 |
| RF-PE4-003 | ADR-007 | casos de uso/API de gestão | apagamento total/corrigir/esquecer + restart | tombstones sem conteúdo |
| LGPD-PE4-001 | ADR-007 | política/adaptadores | no-artifact + exclusão | campos minimizados |
| RT-PE4-001 | ADR-007/008 | retriever/sanitizer limitado | input hostil + caps 8/1.024/2.048 | contexto sanitizado |
| RT-PE4-002 | ADR-007 | migração aditiva + feature gate | forward/rollback-mode/reativação | todos os dados preservados |
