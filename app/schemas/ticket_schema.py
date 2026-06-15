from datetime import date, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IssueType(str, Enum):
    """Issue type classification for service engineer assignment"""
    WORKSHOP = "WORKSHOP"
    ACCIDENT = "ACCIDENT"
    BATTERY_DISCONNECT = "BATTERY_DISCONNECT"
    GPS_REMOVED = "GPS_REMOVED"
    GPS_DAMAGED = "GPS_DAMAGED"
    VEHICLE_RUNNING = "VEHICLE_RUNNING"
    VEHICLE_STANDING = "VEHICLE_STANDING"
    UNKNOWN = "UNKNOWN"


class TicketCreate(BaseModel):
    customer_phone: str
    problem: str
    driver_phone: Optional[str] = None
    customer_id: Optional[int] = None
    driver_id: Optional[int] = None
    
    # Service Engineer Assignment Fields
    issue_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    owner_name: Optional[str] = None
    owner_mobile: Optional[str] = None
    driver_name: Optional[str] = None
    driver_mobile: Optional[str] = None
    location: Optional[str] = None
    visit_date: Optional[date] = None
    visit_time: Optional[time] = None
    reinstallation_date: Optional[date] = None
    reinstallation_time: Optional[time] = None
    vehicle_available: Optional[bool] = None
    vehicle_available_date: Optional[date] = None
    vehicle_available_time: Optional[time] = None
    inspection_date: Optional[date] = None
    inspection_time: Optional[time] = None
    standing_duration: Optional[str] = None


class TicketUpdate(BaseModel):
    """Schema for updating ticket fields"""
    status: Optional[str] = None
    closure_reason: Optional[str] = None
    assigned_engineer_id: Optional[int] = None
    issue_type: Optional[str] = None
    location: Optional[str] = None
    visit_date: Optional[date] = None
    visit_time: Optional[time] = None
    inspection_date: Optional[date] = None
    inspection_time: Optional[time] = None
    vehicle_available: Optional[bool] = None


class TicketOut(BaseModel):
    ticket_number: str
    customer_phone: str
    driver_phone: Optional[str] = None
    problem: str
    status: str
    
    # Service Engineer Assignment Fields
    issue_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    owner_name: Optional[str] = None
    owner_mobile: Optional[str] = None
    driver_name: Optional[str] = None
    driver_mobile: Optional[str] = None
    location: Optional[str] = None
    visit_date: Optional[date] = None
    visit_time: Optional[time] = None
    reinstallation_date: Optional[date] = None
    reinstallation_time: Optional[time] = None
    vehicle_available: Optional[bool] = None
    vehicle_available_date: Optional[date] = None
    vehicle_available_time: Optional[time] = None
    inspection_date: Optional[date] = None
    inspection_time: Optional[time] = None
    standing_duration: Optional[str] = None
    closure_reason: Optional[str] = None
    assigned_engineer_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
