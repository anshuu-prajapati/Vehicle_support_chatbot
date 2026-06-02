import logging
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Alert, VehicleStatus

logger = logging.getLogger(__name__)

ALERT_TYPE_VEHICLE_NOT_WORKING = "VEHICLE_OFF_NOT_WORKING"
ALERT_STATUS_OPEN = "OPEN"
ALERT_STATUS_CLOSED = "CLOSED"


def get_open_alerts(db: Session = None) -> List[Alert]:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        return (
            db.query(Alert)
            .filter(Alert.status == ALERT_STATUS_OPEN)
            .order_by(Alert.created_at.desc())
            .all()
        )
    finally:
        if own_session:
            db.close()


def _open_alert_exists(vehicle_id: int, alert_type: str, db: Session = None) -> bool:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        return (
            db.query(Alert)
            .filter(
                Alert.vehicle_id == vehicle_id,
                Alert.alert_type == alert_type,
                Alert.status == ALERT_STATUS_OPEN,
            )
            .first()
            is not None
        )
    finally:
        if own_session:
            db.close()


def create_alert(vehicle_id: int, alert_type: str = ALERT_TYPE_VEHICLE_NOT_WORKING, db: Session = None) -> Optional[Alert]:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        if _open_alert_exists(vehicle_id, alert_type, db=db):
            logger.info(
                "Skipped duplicate open alert for vehicle_id=%s alert_type=%s",
                vehicle_id,
                alert_type,
            )
            return None

        alert = Alert(
            vehicle_id=vehicle_id,
            status=ALERT_STATUS_OPEN,
            alert_type=alert_type,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.info(
            "Created alert vehicle_id=%s alert_type=%s status=%s",
            vehicle_id,
            alert_type,
            ALERT_STATUS_OPEN,
        )
        return alert
    except SQLAlchemyError as err:
        logger.error(
            "Failed to create alert for vehicle_id=%s alert_type=%s: %s",
            vehicle_id,
            alert_type,
            err,
            exc_info=True,
        )
        if own_session:
            db.rollback()
        return None
    finally:
        if own_session:
            db.close()


def detect_alerts(db: Session = None) -> List[Alert]:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        statuses = (
            db.query(VehicleStatus)
            .filter(
                func.lower(VehicleStatus.ign_state) == "off",
                func.lower(VehicleStatus.mode) == "not working",
            )
            .all()
        )

        created_alerts: List[Alert] = []
        for status in statuses:
            alert = create_alert(status.vehicle_id, ALERT_TYPE_VEHICLE_NOT_WORKING, db=db)
            if alert is not None:
                created_alerts.append(alert)

        logger.info(
            "Detected %d vehicles requiring alert creation; created %d new alerts",
            len(statuses),
            len(created_alerts),
        )
        return created_alerts
    finally:
        if own_session:
            db.close()
