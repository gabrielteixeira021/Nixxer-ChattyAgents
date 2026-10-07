from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    Table,
    DateTime,
    Float,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, backref, Session
from src.backend.db.database import Base
from datetime import datetime, timezone


def default_stats() -> dict:
    """The fresh-start persona stats for a new agent state / a new storyline
    (B8). A factory (not a constant) because last_update must be stamped now so
    need-decay has a baseline (ST-01)."""
    return {
        "energy": 100,
        "hunger": 0,
        "happiness": 100,
        "social": 100,
        "is_sleeping": False,
        "last_update": datetime.now(timezone.utc).isoformat(),
        "relationship": {
            "score": 50,
            "dynamic_preferences": ["teasing", "playful"],
            "user_sentiment": "Neutral",
        },
    }


# Junction table for Character <-> Tag (Many-to-Many)
character_tags = Table(
    "character_tags",
    Base.metadata,
    Column(
        "character_id",
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, unique=True, index=True)
    instruction = Column(Text)  # The prompt snippet this tag injects


class User(Base):
    __tablename__ = "users"
    # Only one row may ever be the active local-user persona. Backed by a
    # partial unique index (SQLite only -- this app has a single production
    # backend) so concurrent get-or-create calls fail fast on the second
    # insert instead of silently creating two "active" users.
    __table_args__ = (
        Index(
            "uq_users_single_active",
            "is_active",
            unique=True,
            sqlite_where=text("is_active"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    gender = Column(String)
    is_active = Column(Boolean, default=True)

    persona_description = Column(Text, default="")
    appearance = Column(Text, default="")

    @classmethod
    def get_or_create_active(cls, db: Session) -> "User":
        user = db.query(cls).filter(cls.is_active == True).first()  # noqa: E712
        if user:
            return user
        user = cls(name="User", gender="Unknown", is_active=True)
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            user = db.query(cls).filter(cls.is_active == True).first()  # noqa: E712
        return user


class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    short_description = Column(Text, default="")
    persona_prompt = Column(Text, default="")
    nickname = Column(String, default="")
    scenario = Column(Text, default="")
    first_mes = Column(Text, default="")
    # Extra opening messages beyond first_mes (Tavern-card alternate_greetings).
    # first_mes is greeting #1; these are #2..N, offered as a picker at chat start.
    alternate_greetings = Column(JSON, default=list)
    mes_example = Column(Text, default="")
    content_rating = Column(String, default="limited")
    is_active = Column(Boolean, default=True)
    # Dynamic (default) = needs decay over time + reflection evolves the persona
    # to adapt to the user. Static = persona frozen as authored: no need-decay,
    # no reflection-driven drift. Scene tracking + memory recall still run in
    # both modes (EPIC Phase 3).
    dynamic_persona = Column(Boolean, default=True)

    # Relationships
    tags = relationship("Tag", secondary=character_tags, backref="characters")
    state = relationship(
        "AgentState",
        back_populates="character",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @classmethod
    def get_default(cls, db):
        existing = db.query(cls).first()
        if existing:
            return existing
        default = cls(name="Gemi", description="Playful entity.")
        db.add(default)
        db.flush()
        return default


class Chat(Base):
    """A single named conversation/session with a character. Introduced so a
    character can hold multiple independent storylines: memory, history and
    summary are scoped by (character_id, chat_id), so starting a "New Chat"
    creates a fresh session instead of destroying the previous one, and one
    chat's memories can never poison another. The character's persistent
    persona (relationship/stats on AgentState) is intentionally shared across
    its chats."""

    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    title = Column(String, default="New Chat")
    is_archived = Column(Boolean, default=False)
    # Per-chat snapshot of the conversation-local pointer/summary/counter. While
    # a chat is the character's active chat, AgentState mirrors these live; on a
    # chat switch they are saved here and the incoming chat's are restored.
    # use_alter breaks the chats<->message_nodes FK cycle for DDL ordering
    # (chats.current_message_id -> message_nodes.id and message_nodes.chat_id ->
    # chats.id). Without it, create_all/drop_all can't topologically sort them.
    current_message_id = Column(
        Integer,
        ForeignKey(
            "message_nodes.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_chats_current_message",
        ),
        nullable=True,
    )
    active_summary = Column(Text, default="")
    interaction_count = Column(Integer, default=0)
    # interaction_count at the last successful reflection, so a reflection due on
    # an interval boundary that failed is retried on the next turn instead of
    # skipped forever (RF-04).
    last_reflected_at_count = Column(Integer, default=0)
    # Per-chat persona snapshot (B8, independent storylines): mood/location/
    # clothes/stats now belong to the chat, not globally to the character. The
    # active chat's snapshot is mirrored live on AgentState; switching chats
    # saves the outgoing snapshot here and restores the incoming one, so each
    # storyline has its own relationship score, mood and scene.
    location = Column(String, default="Living Room")
    mood = Column(String, default="Neutral")
    clothes = Column(String, default="Casual")
    stats = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    character = relationship("Character")
    current_message = relationship("MessageNode", foreign_keys=[current_message_id])


class AgentState(Base):
    __tablename__ = "agent_states"
    id = Column(Integer, primary_key=True, index=True)
    # Ownership FK: the agent state is owned by its character and dies with it.
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        # Owning key: an agent state without a character is meaningless, and a
        # UNIQUE index over a nullable column lets SQLite hold multiple NULL rows,
        # half-opening the "one state per character" invariant (ER review B4).
        nullable=False,
    )
    # Pointer FKs: SET NULL, never CASCADE -- deleting the pointed-at message or
    # chat must clear the pointer, not delete the whole agent state.
    current_message_id = Column(
        Integer, ForeignKey("message_nodes.id", ondelete="SET NULL"), nullable=True
    )
    # Pointer to the character's currently-active Chat/session. AgentState's
    # conversation-local fields (current_message_id, active_summary,
    # interaction_count) belong to whichever chat this points at.
    active_chat_id = Column(
        Integer, ForeignKey("chats.id", ondelete="SET NULL"), nullable=True
    )
    interaction_count = Column(Integer, default=0)
    # Mirrors Chat.last_reflected_at_count for the active chat (RF-04).
    last_reflected_at_count = Column(Integer, default=0)
    location = Column(String, default="Living Room")
    mood = Column(String, default="Neutral")
    clothes = Column(String, default="Casual")

    # Needs, Relationships, etc.
    stats = Column(JSON)

    # Active summary of past interactions
    active_summary = Column(Text, default="")

    # Optimistic-concurrency guard: overlapping /chat or /chat/stream calls for
    # the same character (double-send, regenerate-while-streaming) each load
    # their own copy of this row; without this, whichever commits last silently
    # clobbers the other's stats/interaction_count instead of failing loudly.
    version = Column(Integer, nullable=False, default=1)

    character = relationship("Character", back_populates="state")

    __mapper_args__ = {"version_id_col": version}
    current_message = relationship("MessageNode", foreign_keys=[current_message_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.location is None:
            self.location = "Living Room"
        if self.clothes is None:
            self.clothes = "Casual"
        if self.mood is None:
            self.mood = "Neutral"
        if self.interaction_count is None:
            self.interaction_count = 0
        if self.last_reflected_at_count is None:
            self.last_reflected_at_count = 0
        if not self.stats:
            self.stats = default_stats()


class MessageNode(Base):
    __tablename__ = "message_nodes"
    # parent_id is the most-queried predicate in the app (variant COUNT, subtree
    # sweep, branch walk) -- index it, plus composites for the subtree walk and
    # the per-chat active-history fetch (ER review B3).
    __table_args__ = (
        Index("ix_message_nodes_parent_active", "parent_id", "is_active"),
        Index("ix_message_nodes_chat_active_ts", "chat_id", "is_active", "timestamp"),
    )
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(
        Integer, ForeignKey("message_nodes.id"), nullable=True, index=True
    )
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)  # Raw message or sequence JSON
    type = Column(String, default="speech")  # 'thought', 'action', 'speech'
    variant_index = Column(Integer, default=0)
    request_id = Column(String, index=True, nullable=True)
    character_id = Column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    chat_id = Column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), index=True, nullable=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    children = relationship("MessageNode", backref=backref("parent", remote_side=[id]))
    character = relationship("Character")
    user = relationship("User")


class LorebookEntry(Base):
    __tablename__ = "lorebook_entries"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)  # Used as title/name
    keys = Column(JSON, default=list)  # Primary keys/regexes for matching
    secondary_keys = Column(JSON, default=list)
    content = Column(Text)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_global = Column(Boolean, default=False)

    insertion_order = Column(Integer, default=100)
    probability = Column(Integer, default=100)
    scan_depth = Column(Integer, default=5)
    is_constant = Column(Boolean, default=False)
    cooldown_turns = Column(Integer, default=0)

    character = relationship("Character")


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    chat_id = Column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), index=True, nullable=True
    )
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    content = Column(Text)
    summary = Column(Text)
    mood_at_time = Column(String)
    relationship_score = Column(Integer)
    energy_level = Column(Integer)

    character = relationship("Character")


class SamplerPreset(Base):
    __tablename__ = "sampler_presets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_default = Column(Boolean, default=False)

    # Standard samplers
    temperature = Column(Float, default=1.0)
    min_p = Column(Float, default=0.05)
    top_k = Column(Integer, default=0)
    top_p = Column(Float, default=1.0)
    repeat_penalty = Column(Float, default=1.0)

    # DRY (Don't Repeat Yourself)
    dry_multiplier = Column(Float, default=0.0)
    dry_base = Column(Float, default=1.75)
    dry_range = Column(Integer, default=2048)

    # XTC (Exclude Top Choice)
    xtc_threshold = Column(Float, default=0.0)
    xtc_probability = Column(Float, default=0.0)


class SophiaMemory(Base):
    """Selected durable knowledge for the single SophIA MVP identity.

    This table deliberately has no character, chat, session, scene or message
    foreign key. Those are legacy Open-ChatBot concepts and cannot scope PE4.
    """

    __tablename__ = "sophia_memories"
    __table_args__ = (
        UniqueConstraint(
            "identity_key",
            "category",
            "content_fingerprint",
            name="uq_sophia_memory_normalized_content",
        ),
        Index(
            "ix_sophia_memories_identity_status_expiry",
            "identity_key",
            "status",
            "expires_at",
        ),
    )

    id = Column(String(36), primary_key=True)
    identity_key = Column(String(32), nullable=False, default="sophia")
    category = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    content_fingerprint = Column(String(64), nullable=False)
    origin = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False)
    source_type = Column(String(32), nullable=False)
    source_timestamp = Column(DateTime, nullable=False)
    sensitive = Column(Boolean, nullable=False, default=False)
    purpose = Column(String(160), nullable=True)
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class SophiaMemoryAudit(Base):
    """Content-free PE4 operation evidence permitted after erasure."""

    __tablename__ = "sophia_memory_audit"
    __table_args__ = (Index("ix_sophia_memory_audit_memory_id", "memory_id"),)

    id = Column(Integer, primary_key=True)
    memory_id = Column(String(36), nullable=False)
    action = Column(String(32), nullable=False)
    revision = Column(Integer, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
