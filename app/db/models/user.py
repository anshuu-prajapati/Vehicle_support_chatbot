from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)

    phone_number = Column("phone", String(20), unique=True, nullable=False)
    role = Column(String(20), nullable=False, server_default="customer")

    created_at = Column(DateTime(timezone=True), server_default=func.now())