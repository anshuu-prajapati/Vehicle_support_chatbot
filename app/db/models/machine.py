from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True)

    model_name = Column(String(100))

    serial_number = Column(String(100), unique=True)

    owner_id = Column(Integer, ForeignKey("users.id"))