from app.db.database import SessionLocal
from app.db.models.conversation_state import ConversationState

ASK_HELP_TYPE = "ask_help_type"
COLLECT_PROBLEM_DETAILS = "collect_problem_details"
CONFIRM_DRIVER_PRESENT = "confirm_driver_present"
COLLECT_DRIVER_NUMBER = "collect_driver_number"
ASK_DRIVER_PROBLEM_DETAILS = "ask_driver_problem_details"
CONFIRM_TROUBLESHOOT = "confirm_troubleshoot"
ALERT_ACTION = "alert_action"
COLLECT_CONTACT_PHONE = "collect_contact_phone"

# Fleet operation states
FLEET_ALERT_CREATED = "FLEET_ALERT_CREATED"
WAITING_MANAGER_REPLY = "WAITING_MANAGER_REPLY"
WAITING_NEW_CONTACT = "WAITING_NEW_CONTACT"
WAITING_NEW_CONTACT_NAME = "WAITING_NEW_CONTACT_NAME"
WAITING_NEW_CONTACT_PHONE = "WAITING_NEW_CONTACT_PHONE"
CONTACT_DRIVER = "CONTACT_DRIVER"
DRIVER_INVESTIGATION = "DRIVER_INVESTIGATION"
SUMMARY_SENT = "SUMMARY_SENT"
CLOSED = "CLOSED"

VALID_STATES = {
    ASK_HELP_TYPE,
    COLLECT_PROBLEM_DETAILS,
    CONFIRM_DRIVER_PRESENT,
    COLLECT_DRIVER_NUMBER,
    ASK_DRIVER_PROBLEM_DETAILS,
    CONFIRM_TROUBLESHOOT,
    ALERT_ACTION,
    COLLECT_CONTACT_PHONE,
    FLEET_ALERT_CREATED,
    WAITING_MANAGER_REPLY,
    WAITING_NEW_CONTACT,
    WAITING_NEW_CONTACT_NAME,
    WAITING_NEW_CONTACT_PHONE,
    CONTACT_DRIVER,
    DRIVER_INVESTIGATION,
    SUMMARY_SENT,
    CLOSED,
}

VALID_TRANSITIONS = {
    None: {ASK_HELP_TYPE, FLEET_ALERT_CREATED},
    ASK_HELP_TYPE: {COLLECT_PROBLEM_DETAILS, CONFIRM_DRIVER_PRESENT, ASK_HELP_TYPE, FLEET_ALERT_CREATED},
    COLLECT_PROBLEM_DETAILS: {CONFIRM_TROUBLESHOOT},
    CONFIRM_DRIVER_PRESENT: {COLLECT_DRIVER_NUMBER, ASK_HELP_TYPE, FLEET_ALERT_CREATED},
    COLLECT_DRIVER_NUMBER: {ASK_DRIVER_PROBLEM_DETAILS},
    ASK_DRIVER_PROBLEM_DETAILS: {CONFIRM_TROUBLESHOOT},
    CONFIRM_TROUBLESHOOT: {ASK_HELP_TYPE, CLOSED, FLEET_ALERT_CREATED},
    ALERT_ACTION: {COLLECT_CONTACT_PHONE, ALERT_ACTION, WAITING_NEW_CONTACT, CONTACT_DRIVER, FLEET_ALERT_CREATED},
    COLLECT_CONTACT_PHONE: {ALERT_ACTION, WAITING_MANAGER_REPLY, CONTACT_DRIVER, FLEET_ALERT_CREATED},
    FLEET_ALERT_CREATED: {WAITING_MANAGER_REPLY, WAITING_NEW_CONTACT, WAITING_NEW_CONTACT_NAME, CONTACT_DRIVER, FLEET_ALERT_CREATED},
    WAITING_MANAGER_REPLY: {SUMMARY_SENT, CLOSED, WAITING_MANAGER_REPLY, CONTACT_DRIVER, WAITING_NEW_CONTACT, WAITING_NEW_CONTACT_NAME, FLEET_ALERT_CREATED},
    WAITING_NEW_CONTACT: {CONTACT_DRIVER, WAITING_MANAGER_REPLY, FLEET_ALERT_CREATED},
    WAITING_NEW_CONTACT_NAME: {WAITING_NEW_CONTACT_PHONE, FLEET_ALERT_CREATED},
    WAITING_NEW_CONTACT_PHONE: {CONTACT_DRIVER, WAITING_MANAGER_REPLY, FLEET_ALERT_CREATED},
    CONTACT_DRIVER: {DRIVER_INVESTIGATION, SUMMARY_SENT, WAITING_MANAGER_REPLY, FLEET_ALERT_CREATED},
    DRIVER_INVESTIGATION: {SUMMARY_SENT, CLOSED, WAITING_MANAGER_REPLY, FLEET_ALERT_CREATED},
    SUMMARY_SENT: {CLOSED, WAITING_MANAGER_REPLY, FLEET_ALERT_CREATED},
    CLOSED: {CLOSED},
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
            validate_state_name(current_step)
            state.current_step = current_step

        if context is not None:
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
        return create_state(
            phone_number=phone_number,
            current_step=next_step or ASK_HELP_TYPE,
            context=context or {}
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
