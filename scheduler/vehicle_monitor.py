import logging
from typing import Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.alert_service import detect_alerts
from app.services.vehicle_sync_service import sync_vehicles

logger = logging.getLogger(__name__)
_scheduler: Optional[BackgroundScheduler] = None

JOB_ID = "fleet_vehicle_monitor"


def _ensure_logging_configured() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )


def _vehicle_monitor_job() -> None:
    logger.info("Fleet monitoring execution started")
    try:
        synced_count = sync_vehicles()
        created_alerts = detect_alerts()
        logger.info(
            "Fleet monitoring execution completed: synced=%d vehicles created_alerts=%d",
            synced_count,
            len(created_alerts),
        )
    except Exception as err:
        logger.exception("Fleet monitoring execution failed: %s", err)


def _job_listener(event: JobExecutionEvent) -> None:
    if event.code == EVENT_JOB_MISSED:
        logger.warning("Fleet monitoring job missed a scheduled run: %s", event.job_id)
    if event.exception:
        logger.error(
            "Fleet monitoring job raised an exception: %s",
            event.exception,
            exc_info=True,
        )


def _build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _vehicle_monitor_job,
        trigger=IntervalTrigger(minutes=15),
        id=JOB_ID,
        name="Fleet vehicle monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    return scheduler


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _ensure_logging_configured()
        _scheduler = _build_scheduler()
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        logger.info("Fleet monitoring scheduler is already running")
        return

    logger.info("Starting fleet monitoring scheduler")
    try:
        scheduler.start()
        logger.info("Fleet monitoring scheduler started successfully")
    except Exception as err:
        logger.exception("Failed to start fleet monitoring scheduler: %s", err)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        logger.info("Fleet monitoring scheduler has not been initialized")
        return

    if not _scheduler.running:
        logger.info("Fleet monitoring scheduler is not running")
        return

    logger.info("Stopping fleet monitoring scheduler")
    try:
        _scheduler.shutdown(wait=False)
        logger.info("Fleet monitoring scheduler stopped")
    except Exception as err:
        logger.exception("Failed to stop fleet monitoring scheduler: %s", err)
