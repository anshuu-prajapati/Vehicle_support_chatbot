from fastapi import APIRouter

from app.ai.search import search_problem

router = APIRouter(
    prefix="/search",
    tags=["AI Search"]
)

@router.get("/")
def search(query: str):

    results = search_problem(query)

    matches = []

    for point in results.points:
        matches.append({
            "problem": point.payload.get("problem"),
            "description": point.payload.get("description"),
            "score": point.score
        })

    return matches