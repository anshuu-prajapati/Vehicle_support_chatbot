from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False)
    customer_phone = Column(String(20), nullable=False)
    driver_phone = Column(String(20), nullable=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    problem = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, server_default="OPEN")
    created_at = Column(DateTime(timezone=True), server_default=func.now())