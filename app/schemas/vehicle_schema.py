from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class VehicleStatus(str, Enum):
    """Normalized vehicle status enum"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    NOT_WORKING = "NOT_WORKING"
    UNKNOWN = "UNKNOWN"


class VehicleLocation(BaseModel):
    """Vehicle location information"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    last_update: Optional[datetime] = None

    class Config:
        orm_mode = True


class VehicleDetails(BaseModel):
    """Complete vehicle details response"""
    vehicle_number: str = Field(..., description="Vehicle registration number")
    imei: Optional[str] = Field(None, description="Device IMEI number")
    status: VehicleStatus = Field(..., description="Normalized vehicle status")
    last_location: Optional[VehicleLocation] = Field(None, description="Last known location")
    last_update_time: Optional[datetime] = Field(None, description="Last update timestamp")
    owner_name: Optional[str] = Field(None, description="Vehicle owner name")
    owner_phone: Optional[str] = Field(None, description="Vehicle owner phone")
    driver_name: Optional[str] = Field(None, description="Driver name")
    driver_phone: Optional[str] = Field(None, description="Driver phone")
    raw_data: Optional[dict] = Field(None, description="Raw API response data")

    @validator("vehicle_number")
    def normalize_vehicle_number(cls, v: str) -> str:
        """Normalize vehicle number to uppercase without spaces"""
        return v.strip().upper().replace(" ", "")

    class Config:
        orm_mode = True


class VehicleStatusResponse(BaseModel):
    """Vehicle status only response"""
    vehicle_number: str
    status: VehicleStatus
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True


class VehicleLocationResponse(BaseModel):
    """Vehicle location only response"""
    vehicle_number: str
    location: Optional[VehicleLocation]
    status: VehicleStatus

    class Config:
        orm_mode = True


class VehicleSearchResponse(BaseModel):
    """Vehicle search result"""
    vehicle_number: str
    status: VehicleStatus
    owner_name: Optional[str] = None
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True


class NotWorkingVehiclesResponse(BaseModel):
    """Response for not working vehicles list"""
    total_count: int
    vehicles: list[VehicleSearchResponse]

    class Config:
        orm_mode = True


class VehicleAPIHealthResponse(BaseModel):
    """Health check response for vehicle API"""
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    external_api_reachable: bool = Field(..., description="Whether external API is reachable")
    response_time_ms: Optional[float] = Field(None, description="API response time in milliseconds")
    cache_enabled: bool = Field(..., description="Whether Redis cache is enabled")
    cache_healthy: bool = Field(..., description="Whether Redis cache is healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
