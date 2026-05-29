from pydantic import BaseModel


class ProblemCreate(BaseModel):
    title: str
    description: str
    severity: str
    machine_model: str