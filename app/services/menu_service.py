import logging
import re
from typing import Optional
from sqlalchemy.orm import Session

from app.services.conversation_constants import (
    INVALID_MENU_SELECTION_RESPONSE,
    MENU_CHOICES,
    MENU_OPTIONS,
    MenuAction,
)
from app.services.state_manager import ConversationStep, StateManager
from app.db.models.vehicle import Vehicle
from app.db.models.user import User

logger = logging.getLogger("app.menu_service")


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").strip().lower())


class MenuService:
    def __init__(self, state_manager: StateManager, db: Session = None):
        self.state_manager = state_manager
        self.db = db

    def _get_company_name_for_user(self, user_phone: str) -> str:
        """
        Get company name for a user based on their associated vehicle.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            Company name or default company name
        """
        if not self.db:
            return "Tech Solutions Pvt Ltd"
            
        try:
            # First, get the user
            user = self.db.query(User).filter(User.phone_number == user_phone).first()
            if not user:
                logger.warning(f"User not found for phone: {user_phone}")
                return "Tech Solutions Pvt Ltd"
            
            # Find vehicle associated with this user (as manager, supervisor, or driver)
            vehicle = self.db.query(Vehicle).filter(
                (Vehicle.manager_id == user.id) |
                (Vehicle.supervisor_id == user.id) |
                (Vehicle.driver_id == user.id)
            ).first()
            
            if vehicle and vehicle.company_name:
                logger.info(f"Found company name '{vehicle.company_name}' for user {user_phone}")
                return vehicle.company_name
            
            # If no vehicle found or no company name, return default
            logger.info(f"No vehicle/company found for user {user_phone}, using default")
            return "Tech Solutions Pvt Ltd"
            
        except Exception as e:
            logger.error(f"Error getting company name for user {user_phone}: {str(e)}")
            return "Tech Solutions Pvt Ltd"

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
        
        # Get company name and format the message
        company_name = self._get_company_name_for_user(phone_number)
        formatted_message = choice["ask_text"].format(company_name=company_name)
        
        return formatted_message

    def build_invalid_menu_message(self) -> str:
        return INVALID_MENU_SELECTION_RESPONSE
