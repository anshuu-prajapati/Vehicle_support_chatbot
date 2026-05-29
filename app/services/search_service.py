from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models.problem import Problem


def search_problems(
    db: Session,
    query: str
):

    return (
        db.query(Problem)
        .filter(
            or_(
                Problem.title.ilike(f"%{query}%"),
                Problem.description.ilike(f"%{query}%")
            )
        )
        .all()
    )