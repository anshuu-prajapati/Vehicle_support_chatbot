import uuid
import json
from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint, text, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, CHAR
import os

from app.db.database import Base


# Custom UUID type that works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        elif not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


# Custom JSON type that works with both PostgreSQL and SQLite
class JSONType(TypeDecorator):
    """Platform-independent JSON type.
    Uses PostgreSQL's JSONB type, otherwise uses TEXT with JSON serialization.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            # For SQLite, serialize dict to JSON string
            return json.dumps(value) if isinstance(value, dict) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        if dialect.name == 'postgresql':
            return value
        else:
            # For SQLite, deserialize JSON string to dict
            return json.loads(value) if isinstance(value, str) else value


class ConversationState(Base):
    __tablename__ = "conversation_states"
    __table_args__ = (
        UniqueConstraint("phone_number", name="uq_conversation_states_phone_number"),
        Index("ix_conversation_states_phone_number", "phone_number"),
    )

    # Use database-agnostic UUID type
    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    phone_number = Column(String(20), nullable=False, index=True)
    current_step = Column(String(100), nullable=False)
    
    # Use JSONType for cross-database compatibility
    context_json = Column(
        JSONType,
        nullable=False,
        default={}
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
