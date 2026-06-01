import uuid
from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.database import Base


class ConversationState(Base):
    __tablename__ = "conversation_states"
    __table_args__ = (
        UniqueConstraint("phone_number", name="uq_conversation_states_phone_number"),
        Index("ix_conversation_states_phone_number", "phone_number"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    phone_number = Column(String(20), nullable=False, index=True)
    current_step = Column(String(100), nullable=False)
    context_json = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
