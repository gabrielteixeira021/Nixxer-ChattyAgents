from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Host the local llama-server binds to. The per-server PORT is owned by the
    # runner config (models_config.json); this is the single source for the host
    # so it isn't re-hardcoded as a "127.0.0.1" literal across modules.
    LLAMA_HOST: str = "127.0.0.1"
    LLAMA_SERVER_URL: str = "http://127.0.0.1:8080"
    # Embeddings are served by the same consolidated llama-server on 8080 (the
    # runner migrates the old separate :8081 server onto the inference port).
    EMBEDDING_SERVER_URL: str = "http://127.0.0.1:8080"
    DATABASE_URL: str = "sqlite:///./chatbot.db"
    # Vector-memory store location. Redirected to an isolated dir under tests
    # so E2E/unit runs can never write mock memories into the real store
    # (the exact bug that poisoned real chats with test "Baile/Ballroom" data).
    CHROMA_PATH: str = "./chroma_db"
    MODEL_PATH: str = "models/model.gguf"
    DEBUG_LATENCY: bool = False
    E2E_TESTING: bool = False
    # Single source of truth for "this is a unit-test run", detected once in
    # __init__ so modules reference settings.TESTING instead of each independently
    # sniffing sys.modules for "pytest".
    TESTING: bool = False

    # Operational rollback switch for PE4. Disabling it makes every continuous
    # memory use case fail closed while leaving the additive schema and data
    # untouched, so re-enabling restores the same memories.
    SOPHIA_MEMORY_ENABLED: bool = True

    # Minimum cosine similarity (turbovec returns raw cosine in [-1, 1]) a RAG
    # memory must reach to be injected into the prompt. Without this, an
    # unrelated message ("hello") pulls the top-k memories regardless of
    # distance, poisoning the context with stale/hallucinated content. Tunable.
    MEMORY_RELEVANCE_THRESHOLD: float = 0.5

    # Weight of the recency bonus (0..1 of a normalized message-id proxy) blended
    # into memory ranking, so a stale but marginally-similar old memory can't
    # outrank a recent relevant one. Modest by design -- breaks near-ties toward
    # "now" without overriding a clearly-stronger match. See query_memory (RQ-01).
    MEMORY_RECENCY_WEIGHT: float = 0.15

    # Per-(character, chat) memory-store cap. When a scope exceeds this, the
    # oldest MEMORY_CONSOLIDATE_BATCH memories are condensed by the LLM into a
    # single consolidated memory, so the store stays bounded without hard-losing
    # ancient history to eviction (RQ-05). Set to 0 to disable consolidation.
    MEMORY_STORE_CAP: int = 500
    # How many of the oldest memories to fold into one consolidated summary each
    # time the cap is exceeded. Condensing only the oldest slice (not the whole
    # store) keeps recent memories full-fidelity and avoids re-compressing
    # already-condensed text every cycle.
    MEMORY_CONSOLIDATE_BATCH: int = 100

    # Minimum fraction of the usable token budget reserved for conversation
    # history. Without a floor, fixed layer allocations (~1560 tok) exceed the
    # usable budget on small/quantized contexts and history_budget silently
    # collapses to 0 -- the character loses all turn-to-turn recall. See
    # ContextBudgetCalculator.get_budget.
    MIN_HISTORY_BUDGET_RATIO: float = 0.25

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import sys

        self.TESTING = "pytest" in sys.modules

        if self.E2E_TESTING:
            self.DATABASE_URL = "sqlite:///./e2e_test.db"
            self.CHROMA_PATH = "./e2e_chroma_db"
        elif self.TESTING:
            # Isolate the shared vector-store singleton (core/deps.py) so unit
            # tests never read from or write to the real ./chroma_db.
            self.CHROMA_PATH = "./test_chroma_db"

    # LLM Settings for 1-4B Models
    CONTEXT_SIZE: int = 16384
    RESPONSE_SLOT: int = 1024
    TOKEN_PADDING: int = 128

    # Card sizing. Free-text card fields (persona/scenario/description/examples)
    # are NOT hard-capped at a tiny 300 tokens anymore -- a rich persona is the
    # single biggest lever for a small model's characterization, and starving it
    # to ~225 words is why a detailed card read generic. CARD_MAX_TOKENS is a
    # per-field safety ceiling so a pathological card still can't push the master
    # prompt off the top; RECOMMENDED_CARD_TOKENS is a soft UI hint only (the
    # user is free to exceed it).
    CARD_MAX_TOKENS: int = 8000
    RECOMMENDED_CARD_TOKENS: int = 4096
    # Recency anchor (persona voice + current scene, re-injected right before the
    # reply so a small model never loses who it is) token reserve.
    ANCHOR_TOKENS: int = 250
    # Effective raw-history window, kept deliberately small even on a large
    # context: a 4B attends poorly to the middle of a huge window, so persona +
    # anchor must stay salient. Turns older than this are folded into the rolling
    # summary (Phase 4 compaction) rather than dumped raw.
    HISTORY_WINDOW_TOKENS: int = 10000

    # How often (in turns) the background consciousness layer reflects+evolves.
    # Single source for what used to be a bare `20` at ~5 sites.
    REFLECTION_INTERVAL: int = 20

    # LLM HTTP timeouts (seconds). Centralized so they aren't scattered floats.
    LLM_TIMEOUT: float = 120.0
    LLM_STREAM_TIMEOUT: float = 300.0
    HEALTH_CHECK_TIMEOUT: float = 5.0

    N_PREDICT: int = 3072
    REPEAT_PENALTY: float = 1.12
    REPEAT_LAST_N: int = 512
    TEMPERATURE: float = 0.92
    TOP_P: float = 0.95
    MIN_P: float = 0.05
    TOP_K: int = 40
    SMOOTHING_FACTOR: float = 1.5
    DRY_MULTIPLIER: float = 0.0
    DRY_BASE: float = 1.75
    DRY_RANGE: int = 2048
    XTC_THRESHOLD: float = 0.0
    XTC_PROBABILITY: float = 0.0

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
