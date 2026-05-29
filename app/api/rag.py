from fastapi import APIRouter

from app.services.rag_service import ask_question

router = APIRouter(
    prefix="/ask",
    tags=["RAG"]
)

@router.get("/")
def ask(query: str):

    return ask_question(query)