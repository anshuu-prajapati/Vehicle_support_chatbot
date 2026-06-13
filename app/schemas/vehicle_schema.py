from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

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


class VehicleStatusInfo(BaseModel):
    """Vehicle status and power information"""
    ign_state: Optional[str] = None
    power_state: Optional[str] = None
    mode: Optional[str] = None
    last_gps_time: Optional[datetime] = None
    not_working_hours: int = 0

    class Config:
        orm_mode = True


class VehicleStatusUpdateRequest(BaseModel):
    """Request to update vehicle status fields"""
    vehicle_number: str = Field(..., description="Vehicle registration number", example="DL01AB1234")
    latitude: Optional[float] = Field(None, description="GPS latitude coordinate", example=28.6139)
    longitude: Optional[float] = Field(None, description="GPS longitude coordinate", example=77.2090)
    speed: Optional[float] = Field(None, description="Vehicle speed in km/h", example=45.5)
    power_state: Optional[str] = Field(None, description="Vehicle power state", example="on")
    ignition_state: Optional[str] = Field(None, description="Vehicle ignition state", example="on")

    @validator("vehicle_number")
    def normalize_vehicle_number(cls, v: str) -> str:
        """Normalize vehicle number to uppercase without spaces"""
        return v.strip().upper().replace(" ", "")

    @validator("latitude")
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        """Validate latitude is within valid range"""
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @validator("longitude")
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        """Validate longitude is within valid range"""
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @validator("speed")
    def validate_speed(cls, v: Optional[float]) -> Optional[float]:
        """Validate speed is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Speed must be non-negative")
        return v

    @validator("power_state")
    def validate_power_state(cls, v: Optional[str]) -> Optional[str]:
        """Validate power state values"""
        if v is not None:
            valid_states = ["on", "off", "unknown"]
            v_lower = v.lower().strip()
            if v_lower not in valid_states:
                raise ValueError(f"Power state must be one of: {', '.join(valid_states)}")
            return v_lower
        return v

    @validator("ignition_state")
    def validate_ignition_state(cls, v: Optional[str]) -> Optional[str]:
        """Validate ignition state values"""
        if v is not None:
            valid_states = ["on", "off", "unknown"]
            v_lower = v.lower().strip()
            if v_lower not in valid_states:
                raise ValueError(f"Ignition state must be one of: {', '.join(valid_states)}")
            return v_lower
        return v

    class Config:
        orm_mode = True


class VehicleStatusUpdateResponse(BaseModel):
    """Response for vehicle status update operation"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    vehicle_number: str = Field(..., description="Vehicle registration number")
    updated_fields: Dict[str, Any] = Field(..., description="Fields that were updated")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")

    class Config:
        orm_mode = True


class VehicleDetails(BaseModel):
    """Complete vehicle details response"""
    vehicle_number: str = Field(..., description="Vehicle registration number")
    imei: Optional[str] = Field(None, description="Device IMEI number")
    company_name: Optional[str] = Field(None, description="Company name")
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


class VehicleContact(BaseModel):
    """Vehicle contact information"""
    type: str = Field(..., description="Contact type (OWNER, DRIVER)")
    owner_phone: Optional[str] = Field(None, description="Owner phone number")
    driver_phone: Optional[str] = Field(None, description="Driver phone number") 
    is_primary: bool = Field(False, description="Is primary contact")

    class Config:
        orm_mode = True


class BrokenVehicleInfo(BaseModel):
    """Information about a broken vehicle"""
    vehicle_id: int = Field(..., description="Vehicle database ID")
    vehicle_number: str = Field(..., description="Vehicle registration number")
    company_name: Optional[str] = Field(None, description="Company name")
    location: str = Field(..., description="Current vehicle location")
    last_gps_time: Optional[str] = Field(None, description="Last GPS update time")
    alert_created: Optional[str] = Field(None, description="Alert creation time")
    manager_name: str = Field(..., description="Manager name")
    manager_phone: Optional[str] = Field(None, description="Manager phone number")
    contacts: List[VehicleContact] = Field(default_factory=list, description="Vehicle contacts")

    class Config:
        orm_mode = True


class VehicleAlertResponse(BaseModel):
    """Response for vehicle alert operations"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    vehicles_count: int = Field(0, description="Number of broken vehicles found")
    alerts_sent: int = Field(0, description="Number of WhatsApp alerts sent")
    failed_sends: List[Dict[str, Any]] = Field(default_factory=list, description="Failed message sends")
    vehicles_data: List[BrokenVehicleInfo] = Field(default_factory=list, description="Broken vehicles data")

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
