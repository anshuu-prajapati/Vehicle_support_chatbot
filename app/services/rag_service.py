from app.ai.search import search_problem

from app.db.database import SessionLocal
from app.db.models.problem import Problem
from app.db.models.solution import Solution


def ask_question(query: str):

    results = search_problem(query)

    if not results.points:
        return {
            "message": "No matching problem found"
        }

    best_match = results.points[0]

    problem_title = best_match.payload["problem"]

    db = SessionLocal()

    problem = (
        db.query(Problem)
        .filter(Problem.title == problem_title)
        .first()
    )

    solutions = (
        db.query(Solution)
        .filter(Solution.problem_id == problem.id)
        .order_by(Solution.step_number)
        .all()
    )

    return {
        "problem": problem.title,
        "description": problem.description,
        "confidence": best_match.score,
        "solutions": [
            s.description for s in solutions
        ]
    }