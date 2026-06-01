import logging
import re
from typing import Optional

from app.services.conversation_constants import GREETING_KEYWORDS, MENU_TEXT
from app.services.state_manager import ConversationStep, StateManager

logger = logging.getLogger("app.greeting_service")


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").strip().lower())


class GreetingService:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def is_greeting(self, text: str) -> bool:
        normalized = _normalize_text(text)
        return any(
            normalized == keyword
            or normalized.startswith(f"{keyword} ")
            or normalized.endswith(f" {keyword}")
            or f" {keyword} " in f" {normalized} "
            for keyword in GREETING_KEYWORDS
        )

    def send_welcome(self, user_name: Optional[str]) -> str:
        display_name = user_name.strip() if user_name else "sir/ma'am"
        logger.info("Menu displayed", extra={"user_name": display_name})
        return f"Namaste {display_name} Ji 👋\n\n{MENU_TEXT}"

    def route_to_main_menu(self, phone_number: str) -> None:
        self.state_manager.clear_state(phone_number)
        self.state_manager.set_state(phone_number, ConversationStep.MAIN_MENU)
        logger.info("State updated", extra={"phone_number": phone_number, "new_state": ConversationStep.MAIN_MENU.value})
