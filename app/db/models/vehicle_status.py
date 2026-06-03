from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class VehicleStatus(Base):
    __tablename__ = "vehicle_statuses"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    ign_state = Column(String(20))
    mode = Column(String(50))
    location = Column(String(255))
    last_gps_time = Column(DateTime(timezone=True))
    not_working_hours = Column(Integer, default=0, nullable=False)

    # Relationships
    vehicle = relationship("Vehicle")