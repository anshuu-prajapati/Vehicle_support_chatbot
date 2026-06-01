from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        return self.db.query(User).filter(User.phone_number == phone_number).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, phone_number: str, name: Optional[str], role: str) -> User:
        user = User(phone_number=phone_number, name=name, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, name: Optional[str] = None, role: Optional[str] = None) -> User:
        if name is not None:
            user.name = name
        if role is not None:
            user.role = role

        self.db.commit()
        self.db.refresh(user)
        return user
