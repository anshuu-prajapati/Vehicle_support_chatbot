from pydantic import BaseModel


class SolutionCreate(BaseModel):
    problem_id: int
    step_number: int
    description: str