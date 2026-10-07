# Compliance de Privacidade de Dados (GDPR & LGPD)

> O inventário abaixo descreve a aplicação Open-ChatBot herdada. O contrato PE4
> da SophIA é menor: memória durável guarda fatos, preferências e compromissos
> normalizados e selecionados; áudio bruto, transcrições completas e respostas
> completas do modelo não são retidos por padrão. Consulte a
> [ADR-007](../architecture/decisions/adr-007.md).

O Open-ChatBot é totalmente offline por padrão, alinhado aos princípios de minimização de dados e privacy-by-design sob a Lei Geral de Proteção de Dados brasileira (LGPD) e o General Data Protection Regulation (GDPR) europeu.

## 1. Inventário de Dados (Informação Pessoalmente Identificável - PII)
A aplicação armazena os seguintes identificadores locais:
*   **Dados de Perfil de Usuário:** Nome, gênero (armazenados na tabela SQLite `users`).
*   **Dados de Conversa:** Mensagens de chat, pensamentos, ações, timestamps e diários de personagem (armazenados nas tabelas `message_nodes` e `journal_entries`).
*   **Dados de Embeddings:** Hashes vetoriais de alta dimensão de mensagens e lore (armazenados localmente em `/chroma_db`).

## 2. Pilares Centrais de Compliance LGPD & GDPR

### A. Princípio de Soberania Local (Zero Compartilhamento de Dados)
Toda PII é persistida no banco SQLite local (`chatbot.db`) e no store TurboVec local. Nenhum dado de usuário é transmitido para APIs em nuvem ou servidores remotos. Toda a inferência de modelo roda na CPU/GPU local usando o llama.cpp.

### B. Direito ao Apagamento / Direito ao Esquecimento (Art. 16 LGPD / Art. 17 GDPR)
Os usuários têm controle total sobre seus dados.
*   **Purga de Banco de Dados:** Apagar o arquivo de banco de dados local (`chatbot.db`) e o diretório do vector store local (`/chroma_db`) purga imediata e permanentemente todos os registros.
*   **Limpeza de Histórico de Chat:** Limpar conversas via a UI invoca [clear_chat_history](../../../src/backend/api/chat.py), que executa explicitamente queries SQL `DELETE` em `message_nodes` e `journal_entries` para o personagem selecionado, resetando os metadados de estado imediatamente.

### C. Responsabilização (Art. 37 LGPD)
As ações são registradas localmente com um contexto de `request_id` para verificar os fluxos do sistema. Nenhuma telemetria ou log de telemetria vaza para fora do sistema.

### D. Direitos sobre memória SophIA PE4

A PE4 deve oferecer acesso, correção e esquecimento granular da memória
durável. Apagar uma memória remove revisões, representações SQL/vetoriais,
metadata, cache e payload de auditoria depois de restart. Só pode permanecer um
tombstone sem conteúdo com id, ação e timestamp; apagar todo o banco legado não
é considerado o único caminho de exclusão.
