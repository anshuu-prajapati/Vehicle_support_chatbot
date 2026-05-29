from fastapi import APIRouter

from app.db.database import SessionLocal
from app.db.models.solution import Solution

from app.schemas.solution_schema import SolutionCreate

router = APIRouter(prefix="/solutions", tags=["Solutions"])


@router.get("/")
def get_solutions():

    db = SessionLocal()

    return db.query(Solution).all()


@router.post("/")
def create_solution(solution: SolutionCreate):

    db = SessionLocal()

    new_solution = Solution(
        problem_id=solution.problem_id,
        step_number=solution.step_number,
        description=solution.description
    )

    db.add(new_solution)

    db.commit()

    db.refresh(new_solution)

    return new_solution