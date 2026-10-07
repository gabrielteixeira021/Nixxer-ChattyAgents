# Use Case: Engage in High-Immersion Chat (UC-001)

> **Legacy use case:** this belongs to the inherited Open-ChatBot web/RP
> application. It is not a SophIA MVP flow and does not authorize narrative
> text to execute tools or mutate external systems.

## 1. Description
The User interacts with an AI character, receiving a structured response that includes internal thoughts, physical actions, and spoken dialogue, all influenced by the character's current state and tags.

## 2. Actors
*   **User**: The human interactor.
*   **AI Engine**: The backend processing the prompt and state logic.
*   **LLM Service**: The provider of the intelligence (e.g., GPT-4, Claude).

## 3. Pre-conditions
*   User has an active profile (Name/Gender defined).
*   Character is selected and exists in the database.
*   LLM API is reachable.

## 4. Main Flow
1.  **User** submits a text message via the ChatView.
2.  **AI Engine** retrieves the User's name/gender and the Character's tags/persona.
3.  **AI Engine** evaluates Character states (Energy, Hunger, Relationship).
4.  **AI Engine** assembles the final prompt using the Master Prompt rules.
5.  **LLM Service** generates a structured JSON sequence.
6.  **AI Engine** parses the JSON and streams the blocks to the **User**.
7.  **Frontend** renders each block with specific styles (Italic/Bold).
8.  **AI Engine** updates Character states based on the interaction (e.g., slight energy depletion).

## 5. Alternative Flows
*   **[AF-1] Low Energy**: If Energy < 20%, the AI Engine adds a "forced modifier" to the prompt, making the Character act exhausted.
*   **[AF-2] LLM Timeout**: If the LLM Service fails, the AI Engine returns a cached "error personality" response (e.g., "The character seems distant...").

## 6. Post-conditions
*   Message is stored in the Chat History.
*   Character states are updated in the Database.
*   Frontend displays the full rendered response.
