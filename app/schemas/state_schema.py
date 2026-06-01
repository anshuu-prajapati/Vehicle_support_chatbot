from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr


class StateContext(BaseModel):
    vehicle_number: Optional[str] = Field(default="")
    owner_name: Optional[str] = Field(default="")
    owner_phone: Optional[str] = Field(default="")
    driver_name: Optional[str] = Field(default="")
    driver_phone: Optional[str] = Field(default="")
    issue_type: Optional[str] = Field(default="")
    location: Optional[str] = Field(default="")
    ticket_id: Optional[str] = Field(default="")


class StateCreate(BaseModel):
    phone_number: constr(min_length=7, max_length=20)
    current_step: constr(min_length=3, max_length=100)
    context_json: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StateUpdate(BaseModel):
    current_step: Optional[constr(min_length=3, max_length=100)] = None
    context_json: Optional[Dict[str, Any]] = None


class StateResponse(BaseModel):
    id: UUID
    phone_number: str
    current_step: str
    context_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_encoders={UUID: str})
