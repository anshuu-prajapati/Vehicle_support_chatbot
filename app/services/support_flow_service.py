import logging

from app.services.ticket_service import create_ticket
from app.services.state_manager import (
    ConversationStep,
    StateManager,
)

logger = logging.getLogger("app.support_flow")


def _normalize_text(text: str) -> str:
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    return text in ["haan", "haa", "yes", "y", "h"]


def _is_negative(text: str) -> bool:
    return text in ["nahi", "na", "no", "nahin"]


def _is_restart(text: str) -> bool:
    restart_triggers = ["hi", "hii", "hello", "hey", "namaste", "restart", "reset", "start"]
    return any(text == trigger or text.startswith(f"{trigger} ") for trigger in restart_triggers)


def _welcome_message(user_name: str) -> str:
    display_name = user_name or "sir/ma'am"
    return (
        f"Namaste {display_name} ji 👋\n"
        "Aapko kis tarah ki madad chahiye?\n"
        "1. Machine issue\n"
        "2. Engineer chahiye"
    )


def _build_ticket_response(ticket_number: str) -> str:
    return (
        f"Theek hai. Ticket {ticket_number} create kar diya gaya hai.\n"
        "Engineer jaldi contact karega."
    )


def handle_support_message(user, text_body: str, state_manager: StateManager) -> str:
    normalized = _normalize_text(text_body)

    if _is_restart(normalized):
        state_manager.clear_state(user.phone_number)
        state_manager.set_state(user.phone_number, ConversationStep.MAIN_MENU)
        return _welcome_message(user.name)

    state = state_manager.get_state(user.phone_number)
    if state is None:
        state_manager.set_state(user.phone_number, ConversationStep.MAIN_MENU)
        return _welcome_message(user.name)

    current_step = state.current_step
    context = state_manager.get_context(user.phone_number)

    if current_step == ConversationStep.MAIN_MENU.value:
        if normalized in ["1", "1.", "problem", "problem batani hai", "problem batayein", "problem batana hai"]:
            state_manager.update_context(user.phone_number, {"issue_type": "machine_issue"})
            state_manager.set_state(user.phone_number, ConversationStep.VEHICLE_NUMBER)
            return "Kripya apni machine ka vehicle number bhejiye."

        if normalized in ["2", "2.", "engineer", "engineer chahiye", "book service"]:
            state_manager.update_context(user.phone_number, {"issue_type": "engineer_request"})
            state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
            return "Kya driver machine ke paas hai? Haan / Nahi"

        return (
            "Sirf 1 ya 2 bhejein.\n"
            "Aapko kis tarah ki madad chahiye?\n"
            "1. Machine issue\n"
            "2. Engineer chahiye"
        )

    if current_step == ConversationStep.VEHICLE_NUMBER.value:
        state_manager.update_context(user.phone_number, {"vehicle_number": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
        return "Dhanyavaad. Kya driver machine ke paas hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_DRIVER_AVAILABILITY.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user.phone_number, {"driver_phone": user.phone_number})
            state_manager.set_state(user.phone_number, ConversationStep.ASK_LOCATION)
            return "Bataiye, machine ka location kya hai?"

        if _is_negative(normalized):
            state_manager.set_state(user.phone_number, ConversationStep.OWNER_CONFIRMATION)
            return "Kripya owner ka naam aur phone number bhejiye."

        return "Kripya sirf Haan ya Nahi bhejein. Kya driver machine ke paas hai?"

    if current_step == ConversationStep.OWNER_CONFIRMATION.value:
        state_manager.update_context(user.phone_number, {"owner_name": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.DRIVER_HANDOFF)
        return "Thik hai. Kya aap driver handoff karna chahenge? Haan / Nahi"

    if current_step == ConversationStep.DRIVER_HANDOFF.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user.phone_number, {"driver_name": "handoff_requested"})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_LOCATION)
        return "Dhanyavaad. Machine ka location bataiye."

    if current_step == ConversationStep.ASK_LOCATION.value:
        state_manager.update_context(user.phone_number, {"location": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_IGNITION)
        return "Kya ignition on hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_IGNITION.value:
        state_manager.update_context(user.phone_number, {"ignition_status": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_POWER_LED)
        return "Kya power LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_POWER_LED.value:
        state_manager.update_context(user.phone_number, {"power_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_GSM_LED)
        return "Kya GSM LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_GSM_LED.value:
        state_manager.update_context(user.phone_number, {"gsm_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_GPS_LED)
        return "Kya GPS LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_GPS_LED.value:
        state_manager.update_context(user.phone_number, {"gps_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.VERIFY_RESOLUTION)
        return "Kya problem solve ho gayi? Haan / Nahi"

    if current_step == ConversationStep.VERIFY_RESOLUTION.value:
        if _is_affirmative(normalized):
            state_manager.clear_state(user.phone_number)
            return "Bahut achha. Agar kuch aur madad chahiye toh bataiye."

        if _is_negative(normalized):
            ticket = create_ticket(
                customer_phone=user.phone_number,
                problem=context.get("issue_type", "machine_issue"),
                driver_phone=context.get("driver_phone"),
                customer_id=user.id,
            )
            state_manager.update_context(user.phone_number, {"ticket_id": ticket.ticket_number})
            state_manager.set_state(user.phone_number, ConversationStep.TICKET_CONFIRMATION)
            return _build_ticket_response(ticket.ticket_number)

        return "Kripya sirf Haan ya Nahi mein reply dein. Kya problem solve hui?"

    if current_step == ConversationStep.TICKET_CONFIRMATION.value:
        if _is_affirmative(normalized):
            state_manager.clear_state(user.phone_number)
            return "Great. Agar aapko aur madad chahiye toh dobara message karein."
        return "Aap chahte hain ki engineer turant bheja jaaye."

    if current_step == ConversationStep.ENGINEER_REQUEST.value:
        state_manager.clear_state(user.phone_number)
        return _build_ticket_response(context.get("ticket_id", "unknown"))

    logger.debug("Transitioning unknown state %s to MAIN_MENU", current_step)
    state_manager.set_state(user.phone_number, ConversationStep.MAIN_MENU)
    return _welcome_message(user.name)
