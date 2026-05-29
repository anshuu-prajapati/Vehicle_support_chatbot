from sqlalchemy import Column, Integer, String, Text

from app.db.database import Base


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True)

    title = Column(String(255))

    description = Column(Text)

    severity = Column(String(50))

    machine_model = Column(String(100))