from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class FleetConversation(Base):
    __tablename__ = "fleet_conversations"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    state = Column(String(100), nullable=False)
    metadata = Column(JSON, nullable=False, default=dict)

    vehicle = relationship("Vehicle", back_populates="conversations")
