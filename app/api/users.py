from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.db.database import SessionLocal
from app.db.models.user import User
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.services.user_service import normalize_phone_number

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse)
def create_user(user_data: UserCreate):
    """Create a new user (manager, supervisor, driver, customer)"""
    db = SessionLocal()
    try:
        # Normalize phone number
        phone = normalize_phone_number(user_data.phone_number)
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.phone_number == phone).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this phone number already exists")
        
        # Create new user
        new_user = User(
            name=user_data.name,
            phone_number=phone,
            role=user_data.role.lower()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/", response_model=List[UserListResponse])
def get_all_users(role: str = Query(None), skip: int = 0, limit: int = 100):
    """Get all users, optionally filtered by role"""
    db = SessionLocal()
    try:
        query = db.query(User)
        
        if role:
            query = query.filter(User.role == role.lower())
        
        users = query.offset(skip).limit(limit).all()
        return users
    finally:
        db.close()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    """Get a specific user by ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    finally:
        db.close()


@router.get("/phone/{phone_number}", response_model=UserResponse)
def get_user_by_phone(phone_number: str):
    """Get a specific user by phone number"""
    db = SessionLocal()
    try:
        phone = normalize_phone_number(phone_number)
        user = db.query(User).filter(User.phone_number == phone).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    finally:
        db.close()


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate):
    """Update a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if provided
        if user_data.name is not None:
            user.name = user_data.name
        
        if user_data.phone_number is not None:
            phone = normalize_phone_number(user_data.phone_number)
            # Check if phone already exists (and it's not this user)
            existing = db.query(User).filter(
                User.phone_number == phone,
                User.id != user_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Phone number already exists")
            user.phone_number = phone
        
        if user_data.role is not None:
            user.role = user_data.role.lower()
        
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{user_id}")
def delete_user(user_id: int):
    """Delete a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.delete(user)
        db.commit()
        
        return {
            "status": "success",
            "message": f"User {user_id} deleted successfully",
            "user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/role/managers/list", response_model=List[UserListResponse])
def get_managers(skip: int = 0, limit: int = 100):
    """Get all managers"""
    db = SessionLocal()
    try:
        managers = db.query(User).filter(User.role == "manager").offset(skip).limit(limit).all()
        return managers
    finally:
        db.close()


@router.get("/role/supervisors/list", response_model=List[UserListResponse])
def get_supervisors(skip: int = 0, limit: int = 100):
    """Get all supervisors"""
    db = SessionLocal()
    try:
        supervisors = db.query(User).filter(User.role == "supervisor").offset(skip).limit(limit).all()
        return supervisors
    finally:
        db.close()


@router.get("/role/drivers/list", response_model=List[UserListResponse])
def get_drivers(skip: int = 0, limit: int = 100):
    """Get all drivers"""
    db = SessionLocal()
    try:
        drivers = db.query(User).filter(User.role == "driver").offset(skip).limit(limit).all()
        return drivers
    finally:
        db.close()
