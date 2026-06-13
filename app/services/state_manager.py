import logging
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.repositories.conversation_state_repository import ConversationStateRepository
from app.db.models.conversation_state import ConversationState
from app.services.user_service import normalize_phone_number

logger = logging.getLogger("app.state_manager")


def _merge_context(existing: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing or {})
    merged.update({k: v for k, v in (updates or {}).items() if v is not None})
    return merged


class ConversationStep(str, Enum):
    MAIN_MENU = "MAIN_MENU"
    ASK_RIGHT_PERSON = "ASK_RIGHT_PERSON"
    ASK_CAN_PROVIDE_OTHER_NUMBER = "ASK_CAN_PROVIDE_OTHER_NUMBER"
    ASK_CONTACT_TYPE = "ASK_CONTACT_TYPE"
    ASK_PROBLEM_DESCRIPTION = "ASK_PROBLEM_DESCRIPTION"
    ASK_CONTACT_NUMBER = "ASK_CONTACT_NUMBER"
    GPS_REPAIR_NEAR_VEHICLE = "GPS_REPAIR_NEAR_VEHICLE"
    GPS_REPAIR_TIME_ESTIMATE = "GPS_REPAIR_TIME_ESTIMATE"
    GPS_REPAIR_WAITING_FOR_DRIVER = "GPS_REPAIR_WAITING_FOR_DRIVER"
    GPS_REPAIR_CHECK_IGNITION = "GPS_REPAIR_CHECK_IGNITION"
    GPS_REPAIR_CUT_OUT = "GPS_REPAIR_CUT_OUT"
    GPS_REPAIR_IGNITION = "GPS_REPAIR_IGNITION"
    GPS_REPAIR_VERIFICATION = "GPS_REPAIR_VERIFICATION"
    GPS_REPAIR_RECHECK = "GPS_REPAIR_RECHECK"
    GPS_REPAIR_GROUND_WIRE_FIND = "GPS_REPAIR_GROUND_WIRE_FIND"
    GPS_REPAIR_GROUND_WIRE_TOUCH = "GPS_REPAIR_GROUND_WIRE_TOUCH" 
    GPS_REPAIR_GROUND_WIRE_VERIFY = "GPS_REPAIR_GROUND_WIRE_VERIFY"
    GPS_REPAIR_FINAL_CHECK = "GPS_REPAIR_FINAL_CHECK"
    GPS_REPAIR_ENGINEER_DISPATCH = "GPS_REPAIR_ENGINEER_DISPATCH"
    GPS_REPAIR_SCHEDULE_CALLBACK = "GPS_REPAIR_SCHEDULE_CALLBACK"
    VEHICLE_NUMBER = "VEHICLE_NUMBER"
    ASK_DRIVER_AVAILABILITY = "ASK_DRIVER_AVAILABILITY"
    ASK_LOCATION = "ASK_LOCATION"
    ASK_IGNITION = "ASK_IGNITION"
    ASK_POWER_LED = "ASK_POWER_LED"
    ASK_GSM_LED = "ASK_GSM_LED"
    ASK_GPS_LED = "ASK_GPS_LED"
    VERIFY_RESOLUTION = "VERIFY_RESOLUTION"
    TICKET_CONFIRMATION = "TICKET_CONFIRMATION"
    OWNER_CONFIRMATION = "OWNER_CONFIRMATION"
    DRIVER_HANDOFF = "DRIVER_HANDOFF"
    ENGINEER_REQUEST = "ENGINEER_REQUEST"


DEFAULT_STATE_CONTEXT = {
    "vehicle_number": "",
    "owner_name": "",
    "owner_phone": "",
    "driver_name": "",
    "driver_phone": "",
    "issue_type": "",
    "location": "",
    "ticket_id": "",
    "contact_type": "",
}


class StateManager:
    def __init__(self, db: Session, repository: Optional[ConversationStateRepository] = None):
        self.db = db
        self.repository = repository if repository is not None else ConversationStateRepository(db)

    def get_state(self, phone_number: str) -> Optional[ConversationState]:
        normalized_phone = normalize_phone_number(phone_number)
        return self.repository.get_by_phone(normalized_phone)

    def set_state(
        self,
        phone_number: str,
        step: ConversationStep,
        context_json: Optional[Dict[str, Any]] = None,
    ) -> ConversationState:
        normalized_phone = normalize_phone_number(phone_number)
        state = self.repository.get_by_phone(normalized_phone)
        if state:
            return self.repository.update(
                state,
                current_step=step.value,
                context_json=context_json if context_json is not None else state.context_json,
            )

        return self.repository.create(
            phone_number=normalized_phone,
            current_step=step.value,
            context_json=context_json if context_json is not None else DEFAULT_STATE_CONTEXT.copy(),
        )

    def update_context(
        self,
        phone_number: str,
        data: Dict[str, Any],
        current_step: Optional[ConversationStep] = None,
    ) -> ConversationState:
        normalized_phone = normalize_phone_number(phone_number)
        state = self.repository.get_by_phone_for_update(normalized_phone)
        if not state:
            state = self.repository.create(
                phone_number=normalized_phone,
                current_step=(current_step or ConversationStep.MAIN_MENU).value,
                context_json=_merge_context(DEFAULT_STATE_CONTEXT, data),
            )
            return state

        merged_context = _merge_context(state.context_json or DEFAULT_STATE_CONTEXT.copy(), data)
        return self.repository.update(
            state,
            current_step=current_step.value if current_step is not None else state.current_step,
            context_json=merged_context,
        )

    def get_context(self, phone_number: str) -> Dict[str, Any]:
        state = self.get_state(phone_number)
        return dict(state.context_json or DEFAULT_STATE_CONTEXT.copy()) if state else DEFAULT_STATE_CONTEXT.copy()

    def clear_state(self, phone_number: str) -> ConversationState:
        return self.set_state(
            phone_number,
            ConversationStep.MAIN_MENU,
            context_json=DEFAULT_STATE_CONTEXT.copy(),
        )

    def delete_state(self, phone_number: str) -> bool:
        normalized_phone = normalize_phone_number(phone_number)
        return self.repository.delete_by_phone(normalized_phone)


# Convenience functions for backward-compatible imports.

def get_state(phone_number: str, db: Session) -> Optional[ConversationState]:
    return StateManager(db).get_state(phone_number)


def set_state(phone_number: str, step: ConversationStep, db: Session) -> ConversationState:
    return StateManager(db).set_state(phone_number, step)


def update_context(
    phone_number: str,
    data: Dict[str, Any],
    db: Session,
    current_step: Optional[ConversationStep] = None,
) -> ConversationState:
    return StateManager(db).update_context(phone_number, data, current_step=current_step)


def get_context(phone_number: str, db: Session) -> Dict[str, Any]:
    return StateManager(db).get_context(phone_number)


def clear_state(phone_number: str, db: Session) -> ConversationState:
    return StateManager(db).clear_state(phone_number)


def delete_state(phone_number: str, db: Session) -> bool:
    return StateManager(db).delete_state(phone_number)
