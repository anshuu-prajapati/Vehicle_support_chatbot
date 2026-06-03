from pydantic import BaseModel
from typing import Optional


class VehicleCreate(BaseModel):
    vehicle_number: str
    manager_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    driver_id: Optional[int] = None


class VehicleUpdate(BaseModel):
    vehicle_number: Optional[str] = None
    manager_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    driver_id: Optional[int] = None


class VehicleStatusCreate(BaseModel):
    ign_state: Optional[str] = None  # "on", "off"
    mode: Optional[str] = None  # "working", "not working"
    location: Optional[str] = None
    last_gps_time: Optional[str] = None
    not_working_hours: int = 0


class VehicleResponse(BaseModel):
    id: int
    vehicle_number: str
    manager_id: Optional[int]
    supervisor_id: Optional[int]
    driver_id: Optional[int]

    class Config:
        from_attributes = True


class VehicleDetailResponse(BaseModel):
    id: int
    vehicle_number: str
    manager_id: Optional[int]
    supervisor_id: Optional[int]
    driver_id: Optional[int]
    manager: Optional[dict] = None
    supervisor: Optional[dict] = None
    driver: Optional[dict] = None

    class Config:
        from_attributes = True
