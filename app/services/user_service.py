from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models.user import User
from app.repositories.user_repository import UserRepository

VALID_USER_ROLES = {"owner", "driver", "engineer", "admin"}
DEFAULT_USER_ROLE = "driver"


def normalize_phone_number(phone_number: str) -> str:
    if not phone_number:
        return phone_number

    cleaned = "+".join([p for p in phone_number.strip().replace(" ", "").split("+") if p])
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def normalize_name(name: Optional[str], phone_number: str) -> str:
    if not name or name.strip() == "" or name.strip() == phone_number:
        return phone_number
    return name.strip()


def normalize_role(role: Optional[str]) -> str:
    candidate = (role or DEFAULT_USER_ROLE).strip().lower()
    if candidate not in VALID_USER_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_USER_ROLES)}")
    return candidate


def _resolve_db(db: Optional[Session]) -> Tuple[Session, bool]:
    if db is not None:
        return db, False

    return SessionLocal(), True


def get_user_by_id(user_id: int, db: Optional[Session] = None) -> Optional[User]:
    db, close_db = _resolve_db(db)
    try:
        return UserRepository(db).get(user_id)
    finally:
        if close_db:
            db.close()


def get_user_by_phone(phone_number: str, db: Optional[Session] = None) -> Optional[User]:
    normalized = normalize_phone_number(phone_number)
    db, close_db = _resolve_db(db)
    try:
        return UserRepository(db).get_by_phone(normalized)
    finally:
        if close_db:
            db.close()


def list_users(skip: int = 0, limit: int = 100, db: Optional[Session] = None) -> List[User]:
    db, close_db = _resolve_db(db)
    try:
        return UserRepository(db).list(skip=skip, limit=limit)
    finally:
        if close_db:
            db.close()


def create_user(
    phone_number: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    db: Optional[Session] = None,
) -> User:
    normalized_phone = normalize_phone_number(phone_number)
    normalized_role = normalize_role(role)
    normalized_name = normalize_name(name, normalized_phone)

    db, close_db = _resolve_db(db)
    try:
        return UserRepository(db).create(
            phone_number=normalized_phone,
            name=normalized_name,
            role=normalized_role,
        )
    finally:
        if close_db:
            db.close()


def update_user(
    user_id: int,
    name: Optional[str] = None,
    role: Optional[str] = None,
    db: Optional[Session] = None,
) -> User:
    db, close_db = _resolve_db(db)
    try:
        repository = UserRepository(db)
        user = repository.get(user_id)
        if not user:
            raise ValueError("User not found")

        updated_role = normalize_role(role) if role is not None else None
        updated_name = normalize_name(name, user.phone_number) if name is not None else None
        return repository.update(user, name=updated_name, role=updated_role)
    finally:
        if close_db:
            db.close()


def get_or_create_user(
    phone_number: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    db: Optional[Session] = None,
) -> User:
    db, close_db = _resolve_db(db)
    try:
        repository = UserRepository(db)
        normalized_phone = normalize_phone_number(phone_number)
        user = repository.get_by_phone(normalized_phone)
        if user:
            return user

        return repository.create(
            phone_number=normalized_phone,
            name=normalize_name(name, normalized_phone),
            role=normalize_role(role),
        )
    finally:
        if close_db:
            db.close()
