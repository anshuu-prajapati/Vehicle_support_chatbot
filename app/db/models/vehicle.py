from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(100), unique=True, nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    manager = relationship("User", foreign_keys=[manager_id], backref="managed_vehicles")
    supervisor = relationship("User", foreign_keys=[supervisor_id], backref="supervised_vehicles")
    driver = relationship("User", foreign_keys=[driver_id], backref="driven_vehicles")

    status = relationship("VehicleStatus", uselist=False, back_populates="vehicle")
    alerts = relationship("Alert", back_populates="vehicle", cascade="all, delete-orphan")
    conversations = relationship("FleetConversation", back_populates="vehicle", cascade="all, delete-orphan")
