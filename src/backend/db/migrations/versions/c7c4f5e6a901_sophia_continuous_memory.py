"""add isolated continuous SophIA memory

Revision ID: c7c4f5e6a901
Revises: b2f1a9c4d7e3
Create Date: 2026-10-07 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7c4f5e6a901"
down_revision: Union[str, Sequence[str], None] = "b2f1a9c4d7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PE4 without importing or rewriting any legacy conversation data."""
    op.create_table(
        "sophia_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("identity_key", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(), nullable=False),
        sa.Column("sensitive", sa.Boolean(), nullable=False),
        sa.Column("purpose", sa.String(length=160), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identity_key",
            "category",
            "content_fingerprint",
            name="uq_sophia_memory_normalized_content",
        ),
    )
    op.create_index(
        "ix_sophia_memories_identity_status_expiry",
        "sophia_memories",
        ["identity_key", "status", "expires_at"],
        unique=False,
    )
    op.create_table(
        "sophia_memory_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sophia_memory_audit_memory_id",
        "sophia_memory_audit",
        ["memory_id"],
        unique=False,
    )


def downgrade() -> None:
    """PE4 rollback is operational until a lossless data round trip is proven."""
    raise RuntimeError(
        "PE4 destructive downgrade is forbidden; set SOPHIA_MEMORY_ENABLED=false"
    )
