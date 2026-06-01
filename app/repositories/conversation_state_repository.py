from typing import Optional
from sqlalchemy.orm import Session

from app.db.models.conversation_state import ConversationState


class ConversationStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_phone(self, phone_number: str) -> Optional[ConversationState]:
        return (
            self.db.query(ConversationState)
            .filter(ConversationState.phone_number == phone_number)
            .first()
        )

    def get_by_phone_for_update(self, phone_number: str) -> Optional[ConversationState]:
        return (
            self.db.query(ConversationState)
            .with_for_update()
            .filter(ConversationState.phone_number == phone_number)
            .first()
        )

    def create(
        self,
        phone_number: str,
        current_step: str,
        context_json: Optional[dict] = None,
    ) -> ConversationState:
        state = ConversationState(
            phone_number=phone_number,
            current_step=current_step,
            context_json=context_json or {}
        )
        self.db.add(state)
        self.db.commit()
        self.db.refresh(state)
        return state

    def update(
        self,
        state: ConversationState,
        current_step: Optional[str] = None,
        context_json: Optional[dict] = None,
    ) -> ConversationState:
        if current_step is not None:
            state.current_step = current_step
        if context_json is not None:
            state.context_json = context_json

        self.db.commit()
        self.db.refresh(state)
        return state

    def delete_by_phone(self, phone_number: str) -> bool:
        state = self.get_by_phone(phone_number)
        if not state:
            return False

        self.db.delete(state)
        self.db.commit()
        return True
