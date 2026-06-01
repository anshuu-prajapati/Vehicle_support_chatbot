from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.user_schema import UserCreate, UserRead, UserUpdate
from app.services.user_service import (
    create_user,
    get_user_by_id,
    get_user_by_phone,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserRead, status_code=201)
def create_user_endpoint(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_phone(user_in.phone_number, db)
    if existing:
        raise HTTPException(status_code=409, detail="User with this phone number already exists")
    return create_user(user_in.phone_number, user_in.name, user_in.role, db)


@router.get("/", response_model=List[UserRead])
def read_users(
    phone_number: Optional[str] = Query(None, title="Phone number", description="Phone number to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if phone_number:
        user = get_user_by_phone(phone_number, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return [user]
    return list_users(skip, limit, db)


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user_endpoint(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    user = get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return update_user(user_id, user_in.name, user_in.role, db)
