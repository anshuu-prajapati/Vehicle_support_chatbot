from sqlalchemy import Column, Integer, String, ForeignKey

from app.db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    issue = Column(String(255))

    status = Column(String(50), default="OPEN")