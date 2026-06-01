from sqlalchemy import Column, DateTime, Integer, String, Index
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role", "role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    phone_number = Column("phone", String(20), unique=True, index=True, nullable=False)
    role = Column(String(20), nullable=False, server_default="driver")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
