from app.db.database import SessionLocal
from app.db.models.conversation_state import ConversationState


def get_state(phone_number: str):
    db = SessionLocal()

    try:
        return (
            db.query(ConversationState)
            .filter(ConversationState.phone_number == phone_number)
            .first()
        )
    finally:
        db.close()


def create_state(phone_number: str, current_step: str, context: dict = None):
    db = SessionLocal()

    try:
        state = ConversationState(
            phone_number=phone_number,
            current_step=current_step,
            context_json=context or {}
        )
        db.add(state)
        db.commit()
        db.refresh(state)
        return state
    finally:
        db.close()


def update_state(phone_number: str, current_step: str = None, context: dict = None):
    db = SessionLocal()

    try:
        state = (
            db.query(ConversationState)
            .filter(ConversationState.phone_number == phone_number)
            .first()
        )

        if not state:
            return create_state(
                phone_number=phone_number,
                current_step=current_step or "ask_help_type",
                context=context or {}
            )

        if current_step is not None:
            state.current_step = current_step

        if context is not None:
            state.context_json = context

        db.commit()
        db.refresh(state)
        return state
    finally:
        db.close()


def reset_state(phone_number: str):
    db = SessionLocal()

    try:
        state = (
            db.query(ConversationState)
            .filter(ConversationState.phone_number == phone_number)
            .first()
        )

        if state:
            db.delete(state)
            db.commit()
    finally:
        db.close()
