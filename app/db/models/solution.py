from sqlalchemy import Column, Integer, Text, ForeignKey

from app.db.database import Base


class Solution(Base):
    __tablename__ = "solutions"

    id = Column(Integer, primary_key=True)

    problem_id = Column(Integer, ForeignKey("problems.id"))

    step_number = Column(Integer)

    description = Column(Text)