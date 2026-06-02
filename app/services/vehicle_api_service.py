import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException

from app.core.config import GTRAC_API_KEY, GTRAC_BASE_URL

logger = logging.getLogger(__name__)


@dataclass
class VehicleRecord:
    id: Optional[str]
    vehicle_number: Optional[str]
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = None
    status: Optional[str] = None
    driver_name: Optional[str] = None
    manager_name: Optional[str] = None
    supervisor_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vehicle_number": self.vehicle_number,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "status": self.status,
            "driver_name": self.driver_name,
            "manager_name": self.manager_name,
            "supervisor_name": self.supervisor_name,
            "metadata": self.metadata,
        }


def _build_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
    }

    if GTRAC_API_KEY:
        headers["Authorization"] = f"Bearer {GTRAC_API_KEY}"

    return headers


def _extract_person_name(person_data: Any) -> Optional[str]:
    if not isinstance(person_data, dict):
        return None

    return (
        person_data.get("name")
        or person_data.get("fullName")
        or person_data.get("driverName")
        or person_data.get("firstName")
        or person_data.get("lastName")
    )


def _unwrap_vehicle_list(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("vehicles", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload.get(key)

        return [payload]

    return []


def _parse_vehicle(raw_vehicle: Dict[str, Any]) -> VehicleRecord:
    return VehicleRecord(
        id=str(raw_vehicle.get("id") or raw_vehicle.get("vehicleId") or raw_vehicle.get("vin") or ""),
        vehicle_number=(
            raw_vehicle.get("vehicleNumber")
            or raw_vehicle.get("plateNumber")
            or raw_vehicle.get("licensePlate")
            or raw_vehicle.get("registration")
        ),
        make=raw_vehicle.get("make") or raw_vehicle.get("manufacturer"),
        model=raw_vehicle.get("model"),
        year=raw_vehicle.get("year") or raw_vehicle.get("modelYear"),
        status=raw_vehicle.get("status") or raw_vehicle.get("vehicleStatus"),
        driver_name=_extract_person_name(raw_vehicle.get("driver") or raw_vehicle.get("assignedDriver")),
        manager_name=_extract_person_name(raw_vehicle.get("manager") or raw_vehicle.get("fleetManager")),
        supervisor_name=_extract_person_name(raw_vehicle.get("supervisor") or raw_vehicle.get("teamSupervisor")),
        metadata=raw_vehicle,
    )


def _build_url(path: str) -> str:
    if not GTRAC_BASE_URL:
        raise ValueError("GTRAC_BASE_URL is not configured")

    return f"{GTRAC_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def fetch_vehicles() -> List[VehicleRecord]:
    try:
        url = _build_url("vehicles")
    except ValueError as err:
        logger.error("Vehicle API configuration error: %s", err)
        return []

    headers = _build_headers()
    logger.info("Fetching vehicles from GTRAC API: %s", url)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()
        raw_vehicles = _unwrap_vehicle_list(payload)

        return [_parse_vehicle(item) for item in raw_vehicles]

    except RequestException as err:
        logger.error("Failed to fetch vehicles from GTRAC API: %s", err, exc_info=True)
    except ValueError as err:
        logger.error("Unexpected vehicle API response format: %s", err, exc_info=True)

    return []


def get_vehicle_by_id(vehicle_id: str) -> Optional[VehicleRecord]:
    try:
        url = _build_url(f"vehicles/{vehicle_id}")
    except ValueError as err:
        logger.error("Vehicle API configuration error: %s", err)
        return None

    headers = _build_headers()
    logger.info("Fetching vehicle by ID from GTRAC API: %s", url)

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            logger.warning("Vehicle not found in GTRAC API: %s", vehicle_id)
            return None

        response.raise_for_status()
        payload = response.json()
        raw_vehicle = payload

        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            raw_vehicle = payload["data"]

        return _parse_vehicle(raw_vehicle)

    except RequestException as err:
        logger.error("Failed to fetch vehicle %s from GTRAC API: %s", vehicle_id, err, exc_info=True)
    except ValueError as err:
        logger.error("Unexpected vehicle API response format for %s: %s", vehicle_id, err, exc_info=True)

    return None
