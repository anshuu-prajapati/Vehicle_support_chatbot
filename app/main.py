import logging
import os

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
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Reduce noise from third-party libraries
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.INFO)

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


@app.get("/debug/config")
def debug_config():
    """Check WhatsApp and system configuration"""
    return {
        "whatsapp_configured": bool(os.getenv("META_ACCESS_TOKEN")) and bool(os.getenv("META_PHONE_NUMBER_ID")),
        "verify_token_configured": bool(os.getenv("META_VERIFY_TOKEN")),
        "database_url": "***" if os.getenv("DATABASE_URL") else "NOT SET",
        "webhook_url": "POST /webhook/",
        "verify_url": "GET /webhook/",
        "status": "ready"
    }