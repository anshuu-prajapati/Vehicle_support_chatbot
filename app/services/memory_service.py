from app.db.database import SessionLocal
from app.db.models.chat_message import ChatMessage


def get_last_messages(phone_number: str, limit: int = 10):
    db = SessionLocal()

    try:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.phone_number == phone_number)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def build_history_for_prompt(phone_number: str, limit: int = 10):
    messages = get_last_messages(phone_number, limit)
    messages = list(reversed(messages))
    history_lines = []

    for message in messages:
        user_text = message.user_message.strip() if message.user_message else ""
        bot_text = message.bot_response.strip() if message.bot_response else ""
        history_lines.append(f"User: {user_text}")
        history_lines.append(f"Bot: {bot_text}")

    return "\n".join(history_lines)
