from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr, validator

VALID_USER_ROLES = {"owner", "driver", "engineer", "admin"}


def _normalize_role(role: str) -> str:
    return role.strip().lower()


class UserBase(BaseModel):
    name: Optional[str] = None
    phone_number: constr(min_length=7, max_length=20)
    role: Optional[str] = "driver"

    @validator("role")
    def check_role(cls, value: str) -> str:
        normalized = _normalize_role(value)
        if normalized not in VALID_USER_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_USER_ROLES)}")
        return normalized


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None

    @validator("role")
    def check_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = _normalize_role(value)
        if normalized not in VALID_USER_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_USER_ROLES)}")
        return normalized


class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
