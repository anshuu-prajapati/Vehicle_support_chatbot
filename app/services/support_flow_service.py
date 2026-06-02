from app.services.ai_response_service import generate_ai_answer
from app.services.conversation_state_service import (
    get_state,
    create_state,
    update_state,
    reset_state
)
from app.services.ticket_service import create_ticket
from app.services.user_service import get_or_create_user, normalize_phone_number
from app.services.whatsapp_service import send_whatsapp_message
from app.services.memory_service import build_history_for_prompt


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
        "1. Problem batani hai\n"
        "2. Engineer chahiye"
    )


def _is_alert_option(text: str, option: str) -> bool:
    return text == option or text == f"{option}." or text.startswith(option)


def _build_contact_message(context: dict) -> str:
    return (
        f"Aapko designated contact ke roop mein notify kiya gaya hai.\n"
        f"Vehicle: {context.get('vehicle_number')}\n"
        f"Driver: {context.get('driver_name')}\n"
        f"Location: {context.get('current_location')}\n"
        f"Last GPS Time: {context.get('last_gps_time')}\n"
        "Kripya jaldi se respond karein."
    )


def _handle_alert_action_state(user, state, normalized, text_body: str) -> str:
    context = state.context_json or {}

    if normalized in ["1", "1.", "i am responsible", "i am responsible."]:
        reset_state(user.phone_number)
        return (
            "Samajh gaya. Aapko is alert ke liye responsible maana gaya hai.\n"
            "Hum zarurat padne par aage follow up karenge."
        )

    if normalized in ["2", "2.", "contact another person", "contact another person."]:
        update_state(user.phone_number, "collect_contact_phone", context)
        return "Kripya us vyakti ka WhatsApp phone number bhejiye jise aap contact karna chahte hain."

    if normalized in ["3", "3.", "contact drivers directly", "contact drivers directly."]:
        driver_phone = context.get("driver_phone")
        if not driver_phone:
            update_state(user.phone_number, "collect_contact_phone", context)
            return (
                "Driver ka number system mein available nahi hai.\n"
                "Kripya driver ka phone number bhejiye ya koi dusra contact dijiye."
            )

        contact_message = _build_contact_message(context)
        send_whatsapp_message(driver_phone, contact_message)
        update_state(user.phone_number, "alert_action", context)
        return "Driver ko alert bhej diya gaya hai. Agar aap kisi aur contact se connect karna chahte hain, toh bataiye."

    return (
        "Kripya sirf 1, 2, ya 3 mein reply dein.\n"
        "1. I am responsible\n"
        "2. Contact another person\n"
        "3. Contact drivers directly"
    )


def _handle_collect_contact_phone(user, state, text_body: str) -> str:
    context = state.context_json or {}
    contact_phone = normalize_phone_number(text_body)
    if not contact_phone or len(contact_phone) < 8:
        return "Kripya valid phone number bhejein, country code ke saath."

    updated_context = {**context, "contact_phone": contact_phone}
    update_state(user.phone_number, "alert_action", updated_context)

    get_or_create_user(contact_phone)
    contact_message = _build_contact_message(updated_context)
    send_whatsapp_message(contact_phone, contact_message)

    return (
        "Contact person ko alert bhej diya gaya hai.\n"
        "Aap agar aur koi action lena chahte hain toh bataiye."
    )


def handle_support_message(user, text_body: str) -> str:
    normalized = _normalize_text(text_body)

    if _is_restart(normalized):
        reset_state(user.phone_number)
        create_state(user.phone_number, "ask_help_type", {"user_name": user.name})
        return _welcome_message(user.name)

    state = get_state(user.phone_number)

    if state is None:
        create_state(user.phone_number, "ask_help_type", {"user_name": user.name})
        return _welcome_message(user.name)

    if state.current_step == "alert_action":
        return _handle_alert_action_state(user, state, normalized, text_body)

    if state.current_step == "collect_contact_phone":
        return _handle_collect_contact_phone(user, state, text_body)

    if state.current_step == "ask_help_type":
        if normalized in ["1", "1.", "problem", "problem batani hai", "problem batayein", "problem batana hai"]:
            update_state(user.phone_number, "collect_problem_details", state.context_json or {})
            return "Thik hai. Kripya machine ka problem ek line mein batayein."

        if normalized in ["2", "2.", "engineer", "engineer chahiye", "book service"]:
            update_state(user.phone_number, "confirm_driver_present", state.context_json or {})
            return "Kya driver machine ke paas hai? Haan / Nahi"

        return (
            "Sirf 1 ya 2 bhejein.\n"
            "Aapko kis tarah ki madad chahiye?\n"
            "1. Problem batani hai\n"
            "2. Engineer chahiye"
        )

    if state.current_step == "confirm_driver_present":
        if _is_affirmative(normalized):
            update_state(user.phone_number, "collect_driver_number", state.context_json or {})
            return "Driver ka mobile number bhejiye."

        if _is_negative(normalized):
            update_state(user.phone_number, "ask_help_type", state.context_json or {})
            return "Theek hai. Driver ready ho tab aap dobara message bhej sakte hain."

        return "Kripya sirf Haan ya Nahi bhejein. Kya driver machine ke paas hai?"

    if state.current_step == "collect_driver_number":
        updated_context = {**(state.context_json or {}), "driver_phone": normalized}
        update_state(user.phone_number, "ask_driver_problem_details", updated_context)
        return "Driver se machine mein kya problem aa rahi hai? Ek line mein batayein."

    if state.current_step == "ask_driver_problem_details":
        updated_context = {**(state.context_json or {}), "driver_problem_text": text_body}
        answer = generate_ai_answer(text_body, history=build_history_for_prompt(user.phone_number))
        update_state(
            user.phone_number,
            "confirm_troubleshoot",
            {**updated_context, "problem_text": text_body}
        )
        return f"{answer}\n\nKya problem solve hui? Haan / Nahi"

    if state.current_step == "collect_problem_details":
        updated_context = {**(state.context_json or {}), "problem_text": text_body}
        answer = generate_ai_answer(text_body, history=build_history_for_prompt(user.phone_number))
        update_state(user.phone_number, "confirm_troubleshoot", updated_context)
        return f"{answer}\n\nKya problem solve hui? Haan / Nahi"

    if state.current_step == "confirm_troubleshoot":
        if _is_affirmative(normalized):
            reset_state(user.phone_number)
            return "Bahut achha. Agar kuch aur madad chahiye toh bataiye."

        if _is_negative(normalized):
            context = state.context_json or {}
            driver_phone = context.get("driver_phone")
            problem_text = context.get("problem_text") or text_body
            ticket = create_ticket(
                customer_phone=user.phone_number,
                problem=problem_text,
                driver_phone=driver_phone,
                customer_id=user.id
            )
            reset_state(user.phone_number)
            return (
                f"Theek hai. Ticket {ticket.ticket_number} create kar diya gaya hai.\n"
                "Engineer jaldi contact karega."
            )

        return "Kripya sirf Haan ya Nahi mein reply dein. Kya problem solve hui?"

    update_state(user.phone_number, "ask_help_type", state.context_json or {})
    return _welcome_message(user.name)
