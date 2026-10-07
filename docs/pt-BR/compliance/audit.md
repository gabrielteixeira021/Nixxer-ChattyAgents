# Trilha de Auditoria do Sistema

> **Escopo legado:** esta auditoria descreve chat/inferência do Open-ChatBot.
> Ações narrativas e texto do modelo não comprovam execução de ferramenta da
> SophIA. A auditoria PE4 não retém conteúdo pessoal apagado; sucesso PE5 vem
> somente de resultado estruturado do executor (ADR-007/008).

Para garantir compliance com os critérios padrão de rastreabilidade (RN-005), o backend FastAPI mantém um log de auditoria detalhado e vinculado por rastro para transações conversacionais e ciclos de inferência.

## 1. ID de Correlação de Inferência (`request_id`)
Toda chamada aos endpoints `/chat` ou `/chat/stream` dispara a geração de um ID de correlação único (`request_id`) usando `uuid.uuid4()`. Esse ID vincula todas as atividades em um único ciclo de geração:

*   **Log de API:** O início da execução e a latência da resposta final são marcados com esse ID.
*   **Rastreamento de Banco de Dados:** A tabela `MessageNode` armazena o `request_id` tanto para a mensagem do usuário quanto para a variante de resposta do assistente correspondente.
*   **Logs de Debug:** Erros, avisos de parsing (ex.: falha no formato de validação `RN-003`) e métricas de completion do modelo são emitidos com o prefixo `request_id`.

Consulte [chat.py](../../../src/backend/api/chat.py) para detalhes de implementação.

## 2. Auditoria de Mutação Dinâmica de Estado
Atualizações influenciadas biologicamente (Energia, Fome, score de Relacionamento) são rastreadas em cada interação de chat. Em [chat.py](../../../src/backend/api/chat.py), o helper `parse_actions_to_state()` avalia a resposta narrativa da IA e grava as entradas de auditoria de mutação de estado correspondentes (ex.: mudanças de localização, atualizações de roupa, depleção de fome) diretamente no log da aplicação.

## 3. Integridade e Manutenção do Banco de Dados
*   **Vacuuming:** Ao iniciar, o backend dispara automaticamente queries `VACUUM` para recuperar alocações de página não usadas e preservar a estabilidade estrutural do SQLite. Veja [database.py](../../../src/backend/db/database.py).
*   **Cobertura e Isolamento:** A cobertura de testes exige mocks padrão para impedir que mudanças de desenvolvedor poluam ou modifiquem diretamente o banco de dados de produção (`chatbot.db`).
