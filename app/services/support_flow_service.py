import logging
from typing import Optional

from app.services.greeting_service import GreetingService
from app.services.menu_service import MenuService
from app.services.state_manager import ConversationStep, StateManager
from app.services.ticket_service import create_ticket

logger = logging.getLogger("app.support_flow")


def _normalize_text(text: str) -> str:
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    return text in ["haan", "haa", "yes", "y", "h"]


def _is_negative(text: str) -> bool:
    return text in ["nahi", "na", "no", "nahin"]


def handle_support_message(user, text_body: str, state_manager: StateManager) -> str:
    normalized = _normalize_text(text_body)
    greeting_service = GreetingService(state_manager)
    menu_service = MenuService(state_manager)

    if greeting_service.is_greeting(normalized):
        logger.info(
            "User entered greeting",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)

    state = state_manager.get_state(user.phone_number)
    if state is None:
        logger.info(
            "State not found; initializing MAIN_MENU",
            extra={"phone_number": user.phone_number},
        )
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)

    current_step = state.current_step
    context = state_manager.get_context(user.phone_number)

    if current_step == ConversationStep.MAIN_MENU.value:
        return menu_service.handle_menu_selection(user.phone_number, text_body)

    if current_step == ConversationStep.VEHICLE_NUMBER.value:
        state_manager.update_context(user.phone_number, {"vehicle_number": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_DRIVER_AVAILABILITY.value},
        )
        return (
            "Kripya driver vehicle ke paas hai?\n"
            "1️⃣ Haan\n"
            "2️⃣ Nahi"
        )

    if current_step == ConversationStep.ASK_DRIVER_AVAILABILITY.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user.phone_number, {"driver_phone": user.phone_number})
            state_manager.set_state(user.phone_number, ConversationStep.ASK_LOCATION)
            logger.info(
                "State updated",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_LOCATION.value},
            )
            return "Bataiye vehicle ka location kya hai?"

        if _is_negative(normalized):
            state_manager.set_state(user.phone_number, ConversationStep.OWNER_CONFIRMATION)
            logger.info(
                "State updated",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.OWNER_CONFIRMATION.value},
            )
            return "Kripya owner ka naam aur phone number bhejiye."

        logger.warning(
            "Invalid driver availability response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "Kripya valid option select kare.\n"
            "1️⃣ Haan\n"
            "2️⃣ Nahi"
        )

    if current_step == ConversationStep.OWNER_CONFIRMATION.value:
        state_manager.update_context(user.phone_number, {"owner_name": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.DRIVER_HANDOFF)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.DRIVER_HANDOFF.value},
        )
        return "Thik hai. Kya aap driver handoff karna chahenge? Haan / Nahi"

    if current_step == ConversationStep.DRIVER_HANDOFF.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user.phone_number, {"driver_name": "handoff_requested"})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_LOCATION)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_LOCATION.value},
        )
        return "Dhanyavaad. Machine ka location bataiye."

    if current_step == ConversationStep.ASK_LOCATION.value:
        state_manager.update_context(user.phone_number, {"location": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_IGNITION)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_IGNITION.value},
        )
        return "Kya ignition on hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_IGNITION.value:
        state_manager.update_context(user.phone_number, {"ignition_status": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_POWER_LED)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_POWER_LED.value},
        )
        return "Kya power LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_POWER_LED.value:
        state_manager.update_context(user.phone_number, {"power_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_GSM_LED)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_GSM_LED.value},
        )
        return "Kya GSM LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_GSM_LED.value:
        state_manager.update_context(user.phone_number, {"gsm_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_GPS_LED)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_GPS_LED.value},
        )
        return "Kya GPS LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_GPS_LED.value:
        state_manager.update_context(user.phone_number, {"gps_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.VERIFY_RESOLUTION)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.VERIFY_RESOLUTION.value},
        )
        return "Kya problem solve ho gayi? Haan / Nahi"

    if current_step == ConversationStep.VERIFY_RESOLUTION.value:
        if _is_affirmative(normalized):
            state_manager.clear_state(user.phone_number)
            logger.info("State cleared after resolution", extra={"phone_number": user.phone_number})
            return "Bahut achha. Agar kuch aur madad chahiye toh bataiye."

        if _is_negative(normalized):
            ticket = create_ticket(
                customer_phone=user.phone_number,
                problem=context.get("issue_type", "vehicle_problem"),
                driver_phone=context.get("driver_phone"),
                customer_id=user.id,
            )
            state_manager.update_context(user.phone_number, {"ticket_id": ticket.ticket_number})
            state_manager.set_state(user.phone_number, ConversationStep.TICKET_CONFIRMATION)
            logger.info(
                "Ticket created",
                extra={"phone_number": user.phone_number, "ticket_number": ticket.ticket_number},
            )
            return (
                f"Theek hai. Ticket {ticket.ticket_number} create kar diya gaya hai.\n"
                "Engineer jaldi contact karega."
            )

        logger.warning(
            "Invalid resolution response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return "Kripya sirf Haan ya Nahi mein reply dein. Kya problem solve hui?"

    if current_step == ConversationStep.TICKET_CONFIRMATION.value:
        if _is_affirmative(normalized):
            state_manager.clear_state(user.phone_number)
            return "Great. Agar aapko aur madad chahiye toh dobara message karein."
        return "Aap chahte hain ki engineer turant bheja jaaye."

    logger.debug("Transitioning unknown state %s to MAIN_MENU", current_step)
    greeting_service.route_to_main_menu(user.phone_number)
    return greeting_service.send_welcome(user.name)
