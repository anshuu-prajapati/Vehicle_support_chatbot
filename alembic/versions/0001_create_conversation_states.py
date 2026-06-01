"""create conversation_states table

Revision ID: 0001_create_conversation_states
Revises: 
Create Date: 2026-06-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_create_conversation_states"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "conversation_states",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=False),
        sa.Column(
            "context_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("phone_number", name="uq_conversation_states_phone_number"),
    )
    op.create_index(
        "ix_conversation_states_phone_number",
        "conversation_states",
        ["phone_number"],
    )
    op.create_index(
        "ix_conversation_states_current_step",
        "conversation_states",
        ["current_step"],
    )


def downgrade():
    op.drop_index("ix_conversation_states_current_step", table_name="conversation_states")
    op.drop_index("ix_conversation_states_phone_number", table_name="conversation_states")
    op.drop_table("conversation_states")
