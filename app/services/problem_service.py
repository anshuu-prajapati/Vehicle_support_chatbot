from sqlalchemy.orm import Session

from app.db.models.problem import Problem
from app.db.models.solution import Solution


def get_problem_with_solutions(db: Session, problem_id: int):

    problem = (
        db.query(Problem)
        .filter(Problem.id == problem_id)
        .first()
    )

    if not problem:
        return {"message": "Problem not found"}

    solutions = (
        db.query(Solution)
        .filter(Solution.problem_id == problem_id)
        .order_by(Solution.step_number)
        .all()
    )

    return {
        "problem_id": problem.id,
        "problem": problem.title,
        "description": problem.description,
        "severity": problem.severity,
        "machine_model": problem.machine_model,
        "solutions": [
            {
                "step": s.step_number,
                "description": s.description
            }
            for s in solutions
        ]
    }