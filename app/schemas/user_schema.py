from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    name: str
    phone_number: str
    role: str  # "manager", "supervisor", "driver", "customer"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: Optional[str]
    phone_number: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    id: int
    name: Optional[str]
    phone_number: str
    role: str

    class Config:
        from_attributes = True
