from fastapi import APIRouter
from app.db.database import SessionLocal
from app.db.models.problem import Problem
from app.schemas.problem_schema import ProblemCreate
from app.services.problem_service import get_problem_with_solutions
from app.services.search_service import search_problems

router = APIRouter(prefix="/problems", tags=["Problems"])


@router.get("/")
def get_problems():

    db = SessionLocal()

    return db.query(Problem).all()


@router.post("/")
def create_problem(problem: ProblemCreate):

    db = SessionLocal()

    new_problem = Problem(
        title=problem.title,
        description=problem.description,
        severity=problem.severity,
        machine_model=problem.machine_model
    )

    db.add(new_problem)

    db.commit()

    db.refresh(new_problem)

    return new_problem


@router.get("/{problem_id}")
def get_problem(problem_id: int):

    db = SessionLocal()

    return get_problem_with_solutions(
        db,
        problem_id
    )


@router.get("/search/")
def search(query: str):

    db = SessionLocal()

    return search_problems(
        db,
        query
    )