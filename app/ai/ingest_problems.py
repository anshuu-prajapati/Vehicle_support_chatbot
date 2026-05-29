from qdrant_client.models import PointStruct

from app.ai.embeddings import create_embedding
from app.ai.qdrant_client import client

from app.db.database import SessionLocal
from app.db.models.problem import Problem
from app.db.models.solution import Solution


db = SessionLocal()

problems = db.query(Problem).all()

points = []

for problem in problems:

    solutions = (
        db.query(Solution)
        .filter(
            Solution.problem_id == problem.id
        )
        .all()
    )

    text = f"""
    Problem: {problem.title}

    Description: {problem.description}

    Solutions:
    {" ".join([s.description for s in solutions])}
    """

    vector = create_embedding(text)

    points.append(
        PointStruct(
            id=problem.id,
            vector=vector,
            payload={
                "problem": problem.title,
                "description": problem.description
            }
        )
    )

client.upsert(
    collection_name="machine_problems",
    points=points
)

print("Problems Stored In Qdrant")