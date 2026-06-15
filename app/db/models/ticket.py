from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Time, Boolean
from sqlalchemy.orm import relationship
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
    
    # Service Engineer Assignment Fields
    issue_type = Column(String(50), nullable=True, index=True)
    vehicle_number = Column(String(100), nullable=True, index=True)
    owner_name = Column(String(100), nullable=True)
    owner_mobile = Column(String(20), nullable=True)
    driver_name = Column(String(100), nullable=True)
    driver_mobile = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    visit_date = Column(Date, nullable=True)
    visit_time = Column(Time, nullable=True)
    reinstallation_date = Column(Date, nullable=True)
    reinstallation_time = Column(Time, nullable=True)
    vehicle_available = Column(Boolean, nullable=True)
    vehicle_available_date = Column(Date, nullable=True)
    vehicle_available_time = Column(Time, nullable=True)
    inspection_date = Column(Date, nullable=True)
    inspection_time = Column(Time, nullable=True)
    standing_duration = Column(String(50), nullable=True)
    closure_reason = Column(String(100), nullable=True)
    assigned_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    assigned_engineer = relationship("User", foreign_keys=[assigned_engineer_id])