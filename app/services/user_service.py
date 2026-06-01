from app.db.database import SessionLocal
from app.db.models.user import User


def normalize_phone_number(phone_number: str) -> str:
    if not phone_number:
        return phone_number

    cleaned = "+".join([p for p in phone_number.strip().replace(" ", "").split("+") if p])
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def get_user_by_phone(phone_number: str):
    normalized = normalize_phone_number(phone_number)
    db = SessionLocal()

    try:
        return (
            db.query(User)
            .filter(User.phone_number == normalized)
            .first()
        )
    finally:
        db.close()


def create_user(phone_number: str, name: str = None, role: str = "customer"):
    normalized = normalize_phone_number(phone_number)
    db = SessionLocal()

    try:
        user = User(
            phone_number=normalized,
            name=name or normalized,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def get_or_create_user(phone_number: str, name: str = None, role: str = "customer"):
    user = get_user_by_phone(phone_number)
    if user:
        return user

    return create_user(phone_number, name, role)
