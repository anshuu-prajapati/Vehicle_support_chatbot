import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import User, Vehicle, VehicleStatus
from app.services.vehicle_api_service import VehicleRecord, fetch_vehicles

logger = logging.getLogger(__name__)


def _slugify_name(name: str, max_length: int = 18) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "", name.lower())
    return cleaned[:max_length] or "user"


def _build_placeholder_phone(name: str, role: str) -> str:
    slug = _slugify_name(name)
    prefix = (role or "u")[0].lower()
    return f"{prefix}_{slug}"[:20]


def _get_or_create_user_by_name(db: Session, name: str, role: str) -> Optional[User]:
    if not name:
        return None

    user = db.query(User).filter(User.name == name).first()
    if user:
        return user

    phone = _build_placeholder_phone(name, role)
    candidate_phone = phone
    suffix = 1
    while db.query(User).filter(User.phone_number == candidate_phone).first():
        candidate_phone = f"{phone[:18]}_{suffix}"[:20]
        suffix += 1

    user = User(name=name, phone_number=candidate_phone, role=role or "customer")
    db.add(user)
    db.flush()
    logger.info("Created placeholder user for %s: %s", role, name)
    return user


def _extract_location(metadata: Dict[str, Any]) -> Optional[str]:
    if not isinstance(metadata, dict):
        return None

    location = metadata.get("location") or metadata.get("lastLocation") or metadata.get("deviceLocation")
    if location:
        return str(location)

    latitude = metadata.get("latitude") or metadata.get("lat")
    longitude = metadata.get("longitude") or metadata.get("lng") or metadata.get("lon")
    if latitude is not None and longitude is not None:
        return f"{latitude},{longitude}"

    return None


def _extract_ignition_state(metadata: Dict[str, Any]) -> Optional[str]:
    if not isinstance(metadata, dict):
        return None

    return (
        metadata.get("ign_state")
        or metadata.get("ignState")
        or metadata.get("ignition")
        or metadata.get("ignitionState")
        or metadata.get("engineOn")
    )


def _extract_mode(metadata: Dict[str, Any], fallback_status: Optional[str] = None) -> Optional[str]:
    if not isinstance(metadata, dict):
        return fallback_status

    return (
        metadata.get("mode")
        or metadata.get("vehicleMode")
        or metadata.get("operatingMode")
        or metadata.get("state")
        or fallback_status
    )


def _extract_last_gps_time(metadata: Dict[str, Any]) -> Optional[datetime]:
    if not isinstance(metadata, dict):
        return None

    raw_time = (
        metadata.get("lastGpsTime")
        or metadata.get("gpsTimestamp")
        or metadata.get("timestamp")
        or metadata.get("lastUpdate")
        or metadata.get("updated_at")
    )

    if not raw_time:
        return None

    if isinstance(raw_time, datetime):
        return raw_time

    if isinstance(raw_time, str):
        try:
            return datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            logger.debug("Unable to parse GPS timestamp: %s", raw_time)

    return None


def save_vehicle_status(vehicle: Vehicle, vehicle_data: VehicleRecord, db: Session = None) -> Optional[VehicleStatus]:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        status = (
            db.query(VehicleStatus)
            .filter(VehicleStatus.vehicle_id == vehicle.id)
            .first()
        )

        if status is None:
            status = VehicleStatus(vehicle_id=vehicle.id)
            db.add(status)

        status.location = _extract_location(vehicle_data.metadata)
        status.ign_state = _extract_ignition_state(vehicle_data.metadata)
        status.mode = _extract_mode(vehicle_data.metadata, fallback_status=vehicle_data.status)
        status.last_gps_time = _extract_last_gps_time(vehicle_data.metadata)

        if own_session:
            db.commit()
            db.refresh(status)

        return status

    except SQLAlchemyError as err:
        logger.error("Failed to save status for vehicle %s: %s", vehicle.vehicle_number, err, exc_info=True)
        if own_session:
            db.rollback()
        return None
    finally:
        if own_session:
            db.close()


def save_vehicle(vehicle_data: VehicleRecord) -> Optional[Vehicle]:
    identifier = vehicle_data.vehicle_number or vehicle_data.id
    if not identifier:
        logger.warning("Skipping vehicle with missing identifier: %s", vehicle_data)
        return None

    db = SessionLocal()

    try:
        vehicle = (
            db.query(Vehicle)
            .filter(Vehicle.vehicle_number == identifier)
            .first()
        )

        if vehicle is None:
            vehicle = Vehicle(vehicle_number=identifier)
            db.add(vehicle)
            logger.info("Adding new vehicle %s", identifier)
        else:
            logger.info("Updating existing vehicle %s", identifier)

        if vehicle_data.driver_name:
            driver = _get_or_create_user_by_name(db, vehicle_data.driver_name, "driver")
            vehicle.driver_id = driver.id if driver else None

        if vehicle_data.manager_name:
            manager = _get_or_create_user_by_name(db, vehicle_data.manager_name, "manager")
            vehicle.manager_id = manager.id if manager else None

        if vehicle_data.supervisor_name:
            supervisor = _get_or_create_user_by_name(db, vehicle_data.supervisor_name, "supervisor")
            vehicle.supervisor_id = supervisor.id if supervisor else None

        db.flush()
        save_vehicle_status(vehicle, vehicle_data, db=db)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    except SQLAlchemyError as err:
        logger.error("Failed to save vehicle %s: %s", identifier, err, exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


def sync_vehicles() -> int:
    logger.info("Starting vehicle synchronization")
    vehicles = fetch_vehicles()
    if not vehicles:
        logger.warning("No vehicles fetched from API")
        return 0

    synced = 0
    for vehicle_data in vehicles:
        saved = save_vehicle(vehicle_data)
        if saved:
            synced += 1

    logger.info("Completed vehicle synchronization: %d vehicles synced", synced)
    return synced
