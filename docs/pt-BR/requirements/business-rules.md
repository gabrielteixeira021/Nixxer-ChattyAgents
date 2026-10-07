# Regras de Negócio (RN) — Open-ChatBot

> **Escopo legado:** estas regras governam a aplicação web/RP herdada. Os
> requisitos do MVP SophIA estão em
> [persona-continuity.md](persona-continuity.md). A prioridade da personagem é
> somente estilística e sempre subordinada à política, permissão e resultado
> estruturado real de ferramentas (ADR-008).

## RN-001: Prioridade de Personalidade
O Prompt do Personagem tem precedência somente em conflitos de estilo. Ele
nunca sobrepõe segurança global, política de ferramenta, permissão, argumentos
validados ou resultados factuais.

## RN-002: Limiares de Estado-Comportamento
*   **Energia < 20%**: Modificadores narrativos forçados "lento", "irritado", "cansado".
*   **Fome > 80%**: O diálogo do personagem deve priorizar contexto relacionado a comida ou demonstrar alta impaciência.
*   **Relacionamento > 80%**: Ativa a camada comportamental "Próximo" (mais calor e abertura), sempre dentro das restrições globais de segurança.

## RN-003: Formatação Obrigatória
Qualquer saída de IA que não inclua ao menos um Pensamento (`*...*`) ou Ação (`**...**`) em uma resposta com mais de 50 palavras é sinalizada para regeneração ou aviso no lado do cliente.

## RN-004: Retenção de Memória
Fatos específicos do usuário (Nome, Preferências) devem persistir até que o Usuário exclua explicitamente seu perfil. As "Reflexões" do personagem são resumidas a cada 20 mensagens para prevenir o inchaço do contexto.

## RN-005: Trilha de Auditoria
Toda requisição de API deve ser registrada com um `request_id` único, vinculando o Usuário, o Personagem e a resposta gerada para garantia de qualidade e debugging de compliance.
