from fastapi import FastAPI

from app.db.database import Base
from app.db.database import engine, run_schema_migrations

from app.db.models import *
from app.api.problems import router as problem_router
from app.api.solutions import router as solution_router
from app.api.search import router as search_router
from app.api.rag import router as rag_router
from app.api.users import router as user_router
from app.api.webhook import router as webhook_router




app = FastAPI()

run_schema_migrations()
Base.metadata.create_all(bind=engine)
app.include_router(problem_router)
app.include_router(solution_router)
app.include_router(search_router)
app.include_router(rag_router)
app.include_router(user_router)
app.include_router(webhook_router)


@app.get("/")
def home():
    return {
        "message": "AI Support System Running"
    }