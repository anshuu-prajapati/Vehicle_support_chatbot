from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.database import Base


class VehicleStatus(Base):
    __tablename__ = "vehicle_statuses"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, unique=True)
    ign_state = Column(String(20), nullable=True)
    mode = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    last_gps_time = Column(DateTime(timezone=True), nullable=True)
    not_working_hours = Column(Integer, nullable=False, server_default="0")

    vehicle = relationship("Vehicle", back_populates="status")
