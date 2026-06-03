import logging
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Alert, VehicleStatus
from app.services.conversation_state_service import (
    update_state,
    set_state,
    FLEET_ALERT_CREATED,
)
from app.services.whatsapp_service import send_whatsapp_message

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

        send_alert_to_manager(alert, db=db)

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

        logger.debug("detect_alerts: Found %d vehicles matching 'off' and 'not working' criteria", len(statuses))
        for status in statuses:
            logger.debug("  - Vehicle ID %d: ign_state='%s', mode='%s'", status.vehicle_id, status.ign_state, status.mode)

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


def _format_last_gps_time(last_gps_time):
    if not last_gps_time:
        return "Unknown"
    try:
        return last_gps_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(last_gps_time)


def _build_alert_message(vehicle, status, driver_name, last_gps_time):
    return (
        f"🚨 **FLEET ALERT**\n\n"
        f"Vehicle {vehicle.vehicle_number} NOT WORKING!\n\n"
        f"📋 **Details:**\n"
        f"• Driver: {driver_name}\n"
        f"• Location: {status.location or 'Unknown'}\n"
        f"• Last GPS Update: {last_gps_time}\n\n"
        f"**Kya aap is alert ko handle karenge?**\n"
        f"1. Haan, main handle karunga\n"
        f"2. Kisi aur ko assign karo\n"
        f"3. Driver ko directly contact karo\n\n"
        f"Reply with: 1, 2, or 3"
    )


def _build_alert_context(alert):
    vehicle = alert.vehicle
    status = vehicle.status if vehicle else None
    driver_name = None
    driver_phone = None
    if vehicle and vehicle.driver:
        driver_name = vehicle.driver.name or vehicle.driver.phone_number
        driver_phone = vehicle.driver.phone_number

    return {
        "alert_id": alert.id,
        "vehicle_id": vehicle.id if vehicle else None,
        "vehicle_number": vehicle.vehicle_number if vehicle else None,
        "driver_name": driver_name or "Unknown",
        "current_location": status.location if status else "Unknown",
        "last_gps_time": _format_last_gps_time(status.last_gps_time) if status else "Unknown",
        "driver_phone": driver_phone,
        "manager_phone": vehicle.manager.phone_number if vehicle and vehicle.manager else None,
    }


def send_alert_to_manager(alert: Alert, db: Session = None) -> bool:
    if alert is None or alert.vehicle is None:
        logger.error("send_alert_to_manager: alert or vehicle is None")
        return False

    vehicle = alert.vehicle
    manager = vehicle.manager
    status = vehicle.status

    if manager is None or not manager.phone_number:
        logger.warning(
            "Skipping WhatsApp alert because no manager phone available for vehicle_id=%s",
            vehicle.id,
        )
        return False

    try:
        contact_phone = manager.phone_number
        driver_name = vehicle.driver.name if vehicle.driver and vehicle.driver.name else (vehicle.driver.phone_number if vehicle.driver else "Unknown")
        last_gps_time = _format_last_gps_time(status.last_gps_time) if status else "Unknown"
        message = _build_alert_message(vehicle, status or type("S", (), {"location": None})(), driver_name, last_gps_time)

        # Use set_state to force-set the alert state, bypassing validation
        # This is necessary because alerts can interrupt any ongoing conversation
        logger.debug("Setting conversation state for manager %s to FLEET_ALERT_CREATED", contact_phone)
        set_state(contact_phone, FLEET_ALERT_CREATED, _build_alert_context(alert))
        
        logger.info("Sending WhatsApp message to manager %s for vehicle %s", contact_phone, vehicle.vehicle_number)
        success = send_whatsapp_message(contact_phone, message)
        
        if success:
            logger.info(
                "✓ Successfully sent WhatsApp fleet alert to manager %s for vehicle_id=%s",
                contact_phone,
                vehicle.id,
            )
            return True
        else:
            logger.error(
                "✗ Failed to send WhatsApp fleet alert to manager %s for vehicle_id=%s",
                contact_phone,
                vehicle.id,
            )
            return False
    except Exception as e:
        logger.exception(
            "Exception while sending alert to manager for vehicle_id=%s: %s",
            vehicle.id,
            str(e)
        )
        return False
