import logging

from app.db.database import SessionLocal
from app.db.models.conversation_state import ConversationState

logger = logging.getLogger(__name__)

# Manager/Support states
ASK_HELP_TYPE = "ask_help_type"
COLLECT_PROBLEM_DETAILS = "collect_problem_details"
CONFIRM_TROUBLESHOOT = "confirm_troubleshoot"

# Fleet Alert states - Initial
FLEET_ALERT_CREATED = "FLEET_ALERT_CREATED"

# Fleet Alert states - Manager Response
WAITING_MANAGER_REPLY = "WAITING_MANAGER_REPLY"
WAITING_NEW_CONTACT = "WAITING_NEW_CONTACT"
WAITING_NEW_CONTACT_NAME = "WAITING_NEW_CONTACT_NAME"
WAITING_NEW_CONTACT_PHONE = "WAITING_NEW_CONTACT_PHONE"

# Driver Investigation states
CONTACT_DRIVER = "CONTACT_DRIVER"
DRIVER_INVESTIGATION = "DRIVER_INVESTIGATION"
ASK_DRIVER_STOP_REASON = "ask_driver_stop_reason"
ASK_DRIVER_LOCATION = "ask_driver_location"
ASK_NEED_MECHANIC = "ask_need_mechanic"
ASK_EXPECTED_RESTART_TIME = "ask_expected_restart_time"

# Follow-up states
ASK_ISSUE_RESOLVED = "ask_issue_resolved"
ASK_UNRESOLVED_REASON = "ask_unresolved_reason"

# End states
SUMMARY_SENT = "summary_sent"
CLOSED = "closed"

# Legacy states (kept for backward compatibility)
CONFIRM_DRIVER_PRESENT = "confirm_driver_present"
COLLECT_DRIVER_NUMBER = "collect_driver_number"
ASK_DRIVER_PROBLEM_DETAILS = "ask_driver_problem_details"
ALERT_ACTION = "alert_action"
COLLECT_CONTACT_PHONE = "collect_contact_phone"
ASK_IF_DRIVING = "ASK_IF_DRIVING"
ASK_CAN_PARK = "ASK_CAN_PARK"
TROUBLESHOOT_POWER_LED = "TROUBLESHOOT_POWER_LED"
TROUBLESHOOT_GSM_LED = "TROUBLESHOOT_GSM_LED"
TROUBLESHOOT_GPS_LED = "TROUBLESHOOT_GPS_LED"
ASK_TURN_ON_IGNITION = "ASK_TURN_ON_IGNITION"
ASK_RESOLUTION_CONFIRMATION = "ASK_RESOLUTION_CONFIRMATION"
ESCALATION_SUPPORT_TICKET = "ESCALATION_SUPPORT_TICKET"

VALID_STATES = {
    # Manager/Support states
    ASK_HELP_TYPE,
    COLLECT_PROBLEM_DETAILS,
    CONFIRM_TROUBLESHOOT,
    
    # Fleet Alert states
    FLEET_ALERT_CREATED,
    WAITING_MANAGER_REPLY,
    WAITING_NEW_CONTACT,
    WAITING_NEW_CONTACT_NAME,
    WAITING_NEW_CONTACT_PHONE,
    
    # Driver Investigation states
    CONTACT_DRIVER,
    DRIVER_INVESTIGATION,
    ASK_DRIVER_STOP_REASON,
    ASK_DRIVER_LOCATION,
    ASK_NEED_MECHANIC,
    ASK_EXPECTED_RESTART_TIME,
    
    # Follow-up states
    ASK_ISSUE_RESOLVED,
    ASK_UNRESOLVED_REASON,
    
    # End states
    SUMMARY_SENT,
    CLOSED,
    
    # Legacy states (kept for backward compatibility)
    CONFIRM_DRIVER_PRESENT,
    COLLECT_DRIVER_NUMBER,
    ASK_DRIVER_PROBLEM_DETAILS,
    ALERT_ACTION,
    COLLECT_CONTACT_PHONE,
    ASK_IF_DRIVING,
    ASK_CAN_PARK,
    TROUBLESHOOT_POWER_LED,
    TROUBLESHOOT_GSM_LED,
    TROUBLESHOOT_GPS_LED,
    ASK_TURN_ON_IGNITION,
    ASK_RESOLUTION_CONFIRMATION,
    ESCALATION_SUPPORT_TICKET,
}

VALID_TRANSITIONS = {
    # Initial states
    None: {ASK_HELP_TYPE, FLEET_ALERT_CREATED},
    
    # Manager/Support flow
    ASK_HELP_TYPE: {COLLECT_PROBLEM_DETAILS, CONFIRM_DRIVER_PRESENT, FLEET_ALERT_CREATED},
    COLLECT_PROBLEM_DETAILS: {CONFIRM_TROUBLESHOOT},
    CONFIRM_TROUBLESHOOT: {ASK_HELP_TYPE, CLOSED, FLEET_ALERT_CREATED},
    
    # Fleet Alert flow - Manager receives alert
    FLEET_ALERT_CREATED: {
        WAITING_MANAGER_REPLY,  # Manager says "I will handle"
        WAITING_NEW_CONTACT_NAME,  # Manager says "transfer to another person"
        CONTACT_DRIVER,  # Manager says "contact driver directly"
    },
    
    # Manager handles responsibility
    WAITING_MANAGER_REPLY: {
        CONTACT_DRIVER,  # Manager takes responsibility, contact driver
        WAITING_NEW_CONTACT_NAME,  # Manager transfers to new contact
        CLOSED,  # Manager closes
    },
    
    # Transfer to new contact
    WAITING_NEW_CONTACT_NAME: {WAITING_NEW_CONTACT_PHONE},
    WAITING_NEW_CONTACT_PHONE: {
        CONTACT_DRIVER,  # New contact is the driver
        FLEET_ALERT_CREATED,  # New contact receives alert
    },
    
    # Contact driver for investigation
    CONTACT_DRIVER: {
        DRIVER_INVESTIGATION,
        ASK_DRIVER_STOP_REASON,
    },
    
    # Driver Investigation flow
    DRIVER_INVESTIGATION: {ASK_DRIVER_STOP_REASON},
    ASK_DRIVER_STOP_REASON: {ASK_DRIVER_LOCATION},
    ASK_DRIVER_LOCATION: {ASK_NEED_MECHANIC},
    ASK_NEED_MECHANIC: {ASK_EXPECTED_RESTART_TIME},
    ASK_EXPECTED_RESTART_TIME: {ASK_ISSUE_RESOLVED},
    
    # Follow-up
    ASK_ISSUE_RESOLVED: {
        SUMMARY_SENT,  # Issue resolved
        ASK_UNRESOLVED_REASON,  # Issue not resolved
    },
    ASK_UNRESOLVED_REASON: {SUMMARY_SENT},
    
    # End states
    SUMMARY_SENT: {CLOSED},
    CLOSED: {CLOSED},
    
    # Legacy states (for backward compatibility)
    CONFIRM_DRIVER_PRESENT: {COLLECT_DRIVER_NUMBER, ASK_HELP_TYPE, FLEET_ALERT_CREATED},
    COLLECT_DRIVER_NUMBER: {ASK_DRIVER_PROBLEM_DETAILS},
    ASK_DRIVER_PROBLEM_DETAILS: {CONFIRM_TROUBLESHOOT},
    ALERT_ACTION: {COLLECT_CONTACT_PHONE, ALERT_ACTION, WAITING_NEW_CONTACT},
    COLLECT_CONTACT_PHONE: {ALERT_ACTION, WAITING_MANAGER_REPLY, CONTACT_DRIVER},
    ASK_IF_DRIVING: {ASK_CAN_PARK, ASK_TURN_ON_IGNITION},
    ASK_CAN_PARK: {ASK_TURN_ON_IGNITION, WAITING_MANAGER_REPLY},
    ASK_TURN_ON_IGNITION: {TROUBLESHOOT_POWER_LED},
    TROUBLESHOOT_POWER_LED: {TROUBLESHOOT_GSM_LED, ESCALATION_SUPPORT_TICKET},
    TROUBLESHOOT_GSM_LED: {TROUBLESHOOT_GPS_LED, ESCALATION_SUPPORT_TICKET},
    TROUBLESHOOT_GPS_LED: {ASK_RESOLUTION_CONFIRMATION, ESCALATION_SUPPORT_TICKET},
    ASK_RESOLUTION_CONFIRMATION: {SUMMARY_SENT, ESCALATION_SUPPORT_TICKET},
}


def is_valid_state(step: str) -> bool:
    return step in VALID_STATES


def validate_state_name(step: str):
    if step is None:
        return
    if not is_valid_state(step):
        raise ValueError(f"Invalid conversation state: {step}")


def validate_transition(current_step: str, next_step: str):
    if next_step is None:
        return
    validate_state_name(next_step)

    if current_step == next_step:
        return

    allowed_next_steps = VALID_TRANSITIONS.get(current_step)
    if allowed_next_steps is None:
        raise ValueError(f"No transition rules defined for current state: {current_step}")

    if next_step not in allowed_next_steps:
        raise ValueError(
            f"Invalid conversation state transition from {current_step} to {next_step}"
        )


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
    validate_state_name(current_step)
    db = SessionLocal()

    try:
        logger.info("Creating conversation state for %s -> %s", phone_number, current_step)
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
                current_step=current_step or ASK_HELP_TYPE,
                context=context or {}
            )

        if current_step is not None and current_step != state.current_step:
            validate_transition(state.current_step, current_step)

        if current_step is not None:
            logger.info(
                "Updating conversation state for %s from %s to %s",
                phone_number,
                state.current_step,
                current_step,
            )
            validate_state_name(current_step)
            state.current_step = current_step

        if context is not None:
            logger.debug("Updating conversation context for %s", phone_number)
            state.context_json = context

        db.commit()
        db.refresh(state)
        return state
    finally:
        db.close()


def set_state(phone_number: str, current_step: str, context: dict = None):
    """Set conversation state without validating transition rules.

    This is useful for transferring a conversation to a new phone number
    while preserving the alert context and history.
    """
    validate_state_name(current_step)
    db = SessionLocal()

    try:
        logger.info("Setting conversation state for %s -> %s", phone_number, current_step)
        state = (
            db.query(ConversationState)
            .filter(ConversationState.phone_number == phone_number)
            .first()
        )

        if not state:
            return create_state(
                phone_number=phone_number,
                current_step=current_step,
                context=context or {}
            )

        state.current_step = current_step
        if context is not None:
            state.context_json = context
        db.commit()
        db.refresh(state)
        return state
    finally:
        db.close()


def transition_state(phone_number: str, next_step: str, context: dict = None):
    state = get_state(phone_number)
    if state is None:
        logger.info("Transitioning new conversation state for %s -> %s", phone_number, next_step)
        return create_state(
            phone_number=phone_number,
            current_step=next_step or ASK_HELP_TYPE,
            context=context or {}
        )

    logger.info(
        "Transitioning conversation state for %s from %s to %s",
        phone_number,
        state.current_step,
        next_step,
    )
    validate_transition(state.current_step, next_step)
    return update_state(phone_number, next_step, context or state.context_json)


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
