# Caso de Uso: Engajar em Chat de Alta Imersão (UC-001)

> **Caso de uso legado:** pertence à aplicação web/RP Open-ChatBot herdada. Não
> é fluxo do MVP SophIA e não autoriza texto narrativo a executar ferramentas ou
> alterar sistemas externos.

## 1. Descrição
O Usuário interage com um personagem de IA, recebendo uma resposta estruturada que inclui pensamentos internos, ações físicas e diálogo falado, tudo influenciado pelo estado e tags atuais do personagem.

## 2. Atores
*   **Usuário**: O interator humano.
*   **Motor de IA**: O backend processando o prompt e a lógica de estado.
*   **Serviço de LLM**: O provedor da inteligência (ex.: GPT-4, Claude).

## 3. Pré-condições
*   O Usuário tem um perfil ativo (Nome/Gênero definidos).
*   O Personagem está selecionado e existe no banco de dados.
*   A API do LLM está alcançável.

## 4. Fluxo Principal
1.  O **Usuário** envia uma mensagem de texto via ChatView.
2.  O **Motor de IA** recupera o nome/gênero do Usuário e as tags/persona do Personagem.
3.  O **Motor de IA** avalia os estados do Personagem (Energia, Fome, Relacionamento).
4.  O **Motor de IA** monta o prompt final usando as regras do Master Prompt.
5.  O **Serviço de LLM** gera uma sequência JSON estruturada.
6.  O **Motor de IA** faz o parsing do JSON e transmite os blocos para o **Usuário**.
7.  O **Frontend** renderiza cada bloco com estilos específicos (Itálico/Negrito).
8.  O **Motor de IA** atualiza os estados do Personagem com base na interação (ex.: leve depleção de energia).

## 5. Fluxos Alternativos
*   **[AF-1] Energia Baixa**: Se a Energia < 20%, o Motor de IA adiciona um "modificador forçado" ao prompt, fazendo o Personagem agir de forma exausta.
*   **[AF-2] Timeout do LLM**: Se o Serviço de LLM falhar, o Motor de IA retorna uma resposta em cache de "personalidade de erro" (ex.: "O personagem parece distante...").

## 6. Pós-condições
*   A mensagem é armazenada no Histórico de Chat.
*   Os estados do Personagem são atualizados no Banco de Dados.
*   O Frontend exibe a resposta completa renderizada.
