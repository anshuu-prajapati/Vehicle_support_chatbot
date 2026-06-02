import logging

from fastapi import FastAPI

from app.db.database import Base
from app.db.database import engine, run_schema_migrations
from app.db.models import *
from app.api.problems import router as problem_router
from app.api.solutions import router as solution_router
from app.api.search import router as search_router
from app.api.rag import router as rag_router
from app.api.webhook import router as webhook_router
from scheduler.vehicle_monitor import start_scheduler, stop_scheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI()

run_schema_migrations()
Base.metadata.create_all(bind=engine)
app.include_router(problem_router)
app.include_router(solution_router)
app.include_router(search_router)
app.include_router(rag_router)
app.include_router(webhook_router)


@app.on_event("startup")
def on_startup() -> None:
    logging.getLogger(__name__).info("Running application startup tasks")
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    logging.getLogger(__name__).info("Running application shutdown tasks")
    stop_scheduler()


@app.get("/")
def home():
    return {
        "message": "AI Support System Running"
    }