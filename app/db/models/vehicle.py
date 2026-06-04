from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(100), nullable=False)
    company_name = Column(String(200), nullable=True, default="Tech Solutions Pvt Ltd")
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    manager = relationship("User", foreign_keys=[manager_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    driver = relationship("User", foreign_keys=[driver_id])