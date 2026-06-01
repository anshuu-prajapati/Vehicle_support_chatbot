from app.db.database import SessionLocal
from app.db.models.chat_message import ChatMessage


def save_chat(
    phone_number,
    user_message,
    bot_response
):
    db = SessionLocal()

    try:
        chat = ChatMessage(
            phone_number=phone_number,
            user_message=user_message,
            bot_response=bot_response
        )

        db.add(chat)
        db.commit()
    finally:
        db.close()
