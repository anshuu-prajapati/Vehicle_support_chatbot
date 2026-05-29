from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime

from datetime import datetime

from app.db.database import Base


class ChatMessage(Base):

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)

    phone_number = Column(String)

    user_message = Column(Text)

    bot_response = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )