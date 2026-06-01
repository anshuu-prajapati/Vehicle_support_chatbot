import logging
import re
from typing import Optional

from app.services.conversation_constants import (
    INVALID_MENU_SELECTION_RESPONSE,
    MENU_CHOICES,
    MENU_OPTIONS,
    MenuAction,
)
from app.services.state_manager import ConversationStep, StateManager

logger = logging.getLogger("app.menu_service")


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").strip().lower())


class MenuService:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def _normalize_option(self, text: str) -> Optional[MenuAction]:
        normalized = _normalize_text(text)
        for key, action in MENU_OPTIONS.items():
            if normalized == key:
                return action
            if normalized.startswith(f"{key} "):
                return action
            if normalized.endswith(f" {key}"):
                return action
            if f" {key} " in f" {normalized} ":
                return action
        return None

    def handle_menu_selection(self, phone_number: str, text: str) -> str:
        action = self._normalize_option(text)
        if action is None:
            logger.warning("Invalid selection", extra={"phone_number": phone_number, "raw_text": text})
            return INVALID_MENU_SELECTION_RESPONSE

        choice = MENU_CHOICES[action]
        logger.info("Option selected", extra={"phone_number": phone_number, "selection": action.value})
        self.state_manager.update_context(
            phone_number,
            {"issue_type": choice["issue_type"]},
        )
        self.state_manager.set_state(phone_number, choice["next_state"])
        logger.info(
            "State updated",
            extra={"phone_number": phone_number, "new_state": choice["next_state"].value},
        )
        return choice["ask_text"]

    def build_invalid_menu_message(self) -> str:
        return INVALID_MENU_SELECTION_RESPONSE
