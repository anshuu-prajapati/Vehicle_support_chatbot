import logging
from datetime import datetime

from app.services.ai_response_service import generate_ai_answer
from app.services.conversation_state_service import (
    get_state,
    create_state,
    update_state,
    set_state,
    reset_state,
    FLEET_ALERT_CREATED,
    WAITING_MANAGER_REPLY,
    WAITING_NEW_CONTACT,
    WAITING_NEW_CONTACT_NAME,
    WAITING_NEW_CONTACT_PHONE,
    CONTACT_DRIVER,
    DRIVER_INVESTIGATION,
    ASK_DRIVER_STOP_REASON,
    ASK_DRIVER_LOCATION,
    ASK_NEED_MECHANIC,
    ASK_EXPECTED_RESTART_TIME,
    SUMMARY_SENT,
    CLOSED,
    ASK_IF_DRIVING,
    ASK_CAN_PARK,
    TROUBLESHOOT_POWER_LED,
    TROUBLESHOOT_GSM_LED,
    TROUBLESHOOT_GPS_LED,
    ASK_TURN_ON_IGNITION,
    ASK_RESOLUTION_CONFIRMATION,
    ESCALATION_SUPPORT_TICKET,
)
from app.services.ticket_service import create_ticket
from app.services.user_service import get_or_create_user, normalize_phone_number
from app.services.whatsapp_service import send_whatsapp_message
from app.services.memory_service import build_history_for_prompt

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    return text in ["haan", "haa", "yes", "y", "h"]


def _is_negative(text: str) -> bool:
    return text in ["nahi", "na", "no", "nahin"]


def _is_restart(text: str) -> bool:
    restart_triggers = ["hi", "hii", "hello", "hey", "namaste", "restart", "reset", "start"]
    return any(text == trigger or text.startswith(f"{trigger} ") for trigger in restart_triggers)

SUPPORTED_DRIVER_STOP_REASONS = {
    "1": "breakdown",
    "2": "maintenance",
    "3": "waiting load",
    "4": "leave",
    "5": "other",
    "breakdown": "breakdown",
    "maintenance": "maintenance",
    "waiting load": "waiting load",
    "waiting": "waiting load",
    "wait": "waiting load",
    "load": "waiting load",
    "leave": "leave",
    "other": "other",
}


def _format_supported_reasons() -> str:
    options = ["Breakdown", "Maintenance", "Waiting Load", "Leave", "Other"]
    return " / ".join(options)


def _normalize_reason(text: str) -> str:
    normalized = _normalize_text(text)
    return SUPPORTED_DRIVER_STOP_REASONS.get(normalized)


def _build_driver_investigation_prompt() -> str:
    return (
        "Vehicle kyun ruk gaya?\n"
        "Options:\n"
        "1. Breakdown\n"
        "2. Maintenance\n"
        "3. Waiting Load\n"
        "4. Leave\n"
        "5. Other\n"
        "Kripya upar se ek option bhejein."
    )


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
    message = (
        f"Aapko designated contact ke roop mein notify kiya gaya hai.\n"
        f"Vehicle: {context.get('vehicle_number')}\n"
        f"Driver: {context.get('driver_name')}\n"
        f"Location: {context.get('current_location')}\n"
        f"Last GPS Time: {context.get('last_gps_time')}\n"
    )

    transfer_name = context.get("transfer_contact_name") or context.get("contact_name")
    if transfer_name:
        message += f"Contact Name: {transfer_name}\n"

    message += "Kripya jaldi se respond karein."
    return message


def _build_transfer_alert_message(context: dict) -> str:
    return (
        f"Aapko naye contact ke roop mein notify kiya gaya hai.\n"
        f"Vehicle: {context.get('vehicle_number')}\n"
        f"Driver: {context.get('driver_name')}\n"
        f"Location: {context.get('current_location')}\n"
        f"Last GPS Time: {context.get('last_gps_time')}\n"
        "Kripya jaldi se respond karein.\n\n"
        "Options:\n"
        "1. I am responsible\n"
        "2. Contact another person\n"
        "3. Contact drivers directly\n\n"
        "Please reply with 1, 2, or 3."
    )


def _append_transfer_history(context: dict, contact_name: str, contact_phone: str, transferred_by: str) -> list:
    history = list(context.get("transfer_history", [])) if context else []
    history.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "transferred_by": transferred_by,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "vehicle_id": context.get("vehicle_id") if context else None,
        "alert_id": context.get("alert_id") if context else None,
    })
    return history


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


def _handle_fleet_alert_created_state(user, state, normalized, text_body: str) -> str:
    """Handle manager's response to fleet alert."""
    context = state.context_json or {}

    # Option 1: Manager will handle this issue
    if normalized in ["1", "1.", "haan", "haa", "yes", "handle", "main handle karunga"]:
        # Manager keeps the alert - ask what they want to do
        update_state(user.phone_number, CONTACT_DRIVER, context)
        
        driver_name = context.get("driver_name", "Driver")
        return (
            "Samajh gaya. Aapko is alert ke liye responsible maana gaya hai.\n\n"
            f"Aap kya karna chahte ho?\n"
            f"1. {driver_name} se investigation details lena\n"
            f"2. Khud se investigation karna\n"
            f"3. Kisi aur ko contact karna"
        )

    # Option 2: Assign to someone else
    if normalized in ["2", "2.", "kisi aur ko", "assign", "transfer", "assign karo"]:
        update_state(user.phone_number, WAITING_NEW_CONTACT_NAME, context)
        return "Kripya naye contact ka naam bhejiye."

    # Option 3: Contact driver directly
    if normalized in ["3", "3.", "driver", "driver ko", "directly contact", "contact driver"]:
        driver_phone = context.get("driver_phone")
        if not driver_phone:
            update_state(user.phone_number, WAITING_NEW_CONTACT, context)
            return (
                "Driver ka number system mein available nahi hai.\n"
                "Kripya driver ka phone number bhejiye."
            )

        # Contact driver directly
        contact_message = _build_contact_message(context)
        send_whatsapp_message(driver_phone, contact_message)
        update_state(user.phone_number, WAITING_MANAGER_REPLY, context)
        set_state(driver_phone, CONTACT_DRIVER, context)
        return "Driver ko alert bhej diya gaya hai. Ab driver se investigation karwayein."

    # Invalid response
    return (
        "Kripya sirf 1, 2, ya 3 mein reply dein.\n"
        "1. Haan, main handle karunga\n"
        "2. Kisi aur ko assign karo\n"
        "3. Driver ko directly contact karo"
    )


def _handle_waiting_new_contact_name_state(user, state, text_body: str) -> str:
    contact_name = text_body.strip()
    if not contact_name:
        return "Kripya valid naam bhejiye."

    context = state.context_json or {}
    updated_context = {**context, "transfer_contact_name": contact_name}
    update_state(user.phone_number, WAITING_NEW_CONTACT_PHONE, updated_context)
    return "Kripya naye contact ka WhatsApp phone number bhejiye."


def _handle_waiting_new_contact_phone_state(user, state, text_body: str) -> str:
    context = state.context_json or {}
    contact_phone = normalize_phone_number(text_body)
    if not contact_phone or len(contact_phone) < 8:
        return "Kripya valid phone number bhejein, country code ke saath."

    contact_name = context.get("transfer_contact_name") or context.get("contact_name") or "Contact"
    transfer_history = _append_transfer_history(context, contact_name, contact_phone, user.phone_number)
    updated_context = {
        **context,
        "contact_phone": contact_phone,
        "contact_name": contact_name,
        "transfer_contact_name": contact_name,
        "transfer_contact_phone": contact_phone,
        "transfer_history": transfer_history,
    }

    get_or_create_user(contact_phone, contact_name, role="manager")
    is_driver = contact_phone == context.get("driver_phone")

    if is_driver:
        # Send investigation prompt directly to driver
        investigation_prompt = _build_driver_investigation_prompt()
        send_whatsapp_message(contact_phone, investigation_prompt)
        # Manager stays in WAITING_MANAGER_REPLY - they already delegated
        update_state(user.phone_number, WAITING_MANAGER_REPLY, updated_context)
        # Driver is ready to answer investigation questions
        set_state(contact_phone, ASK_DRIVER_STOP_REASON, updated_context)
        return "Driver ko investigation prompt bhej diya gaya hai.\nJab driver jawab de, aapko update milega."

    contact_message = _build_transfer_alert_message(updated_context)
    send_whatsapp_message(contact_phone, contact_message)
    update_state(user.phone_number, WAITING_MANAGER_REPLY, updated_context)
    set_state(contact_phone, FLEET_ALERT_CREATED, updated_context)

    return (
        "Contact person ko alert bhej diya gaya hai.\n"
        "Vehicle conversation ab naye contact ko transfer kar di gayi hai.\n"
        "Aapko ab unke jawab ke liye update milega."
    )


def _handle_waiting_new_contact_state(user, state, text_body: str) -> str:
    context = state.context_json or {}
    contact_phone = normalize_phone_number(text_body)
    if not contact_phone or len(contact_phone) < 8:
        return "Kripya valid phone number bhejein, country code ke saath."

    updated_context = {**context, "contact_phone": contact_phone}
    contact_message = _build_contact_message(updated_context)
    send_whatsapp_message(contact_phone, contact_message)

    next_state = CONTACT_DRIVER if contact_phone == context.get("driver_phone") else WAITING_MANAGER_REPLY
    update_state(user.phone_number, next_state, updated_context)

    return (
        "Contact person ko alert bhej diya gaya hai.\n"
        "Aap agar aur koi action lena chahte hain toh bataiye."
    )


def _handle_ask_driver_stop_reason_state(user, state, text_body: str) -> str:
    context = state.context_json or {}
    reason = _normalize_reason(text_body)
    if not reason:
        logger.warning("Invalid driver stop reason from %s: %s", user.phone_number, text_body)
        return (
            "Kripya valid reason bhejein. Options: Breakdown, Maintenance, Waiting Load, Leave, Other."
        )

    investigation = {**context.get("driver_investigation", {}), "stop_reason": reason}
    updated_context = {**context, "driver_investigation": investigation}
    update_state(user.phone_number, ASK_DRIVER_LOCATION, updated_context)

    return "Aapka current location kya hai?"


def _handle_ask_driver_location_state(user, state, text_body: str) -> str:
    location = text_body.strip()
    if not location or len(location) < 3:
        logger.warning("Invalid driver location from %s: %s", user.phone_number, text_body)
        return "Kripya valid current location bhejein."

    context = state.context_json or {}
    investigation = {**context.get("driver_investigation", {}), "current_location": location}
    updated_context = {**context, "driver_investigation": investigation}
    update_state(user.phone_number, ASK_NEED_MECHANIC, updated_context)

    return "Kya aapko mechanic ki zarurat hai? Haan / Nahi"


def _handle_ask_need_mechanic_state(user, state, text_body: str) -> str:
    normalized = _normalize_text(text_body)
    if _is_affirmative(normalized):
        mechanic_needed = True
    elif _is_negative(normalized):
        mechanic_needed = False
    else:
        logger.warning("Invalid mechanic answer from %s: %s", user.phone_number, text_body)
        return "Kripya Haan ya Nahi mein jawab dein. Kya aapko mechanic ki zarurat hai?"

    context = state.context_json or {}
    investigation = {**context.get("driver_investigation", {}), "needs_mechanic": mechanic_needed}
    updated_context = {**context, "driver_investigation": investigation}
    update_state(user.phone_number, ASK_EXPECTED_RESTART_TIME, updated_context)

    return "Expected restart time kya hai? (Jaise 30 mins, 2 ghante)"


def _handle_ask_expected_restart_time_state(user, state, text_body: str) -> str:
    restart_time = text_body.strip()
    if not restart_time:
        logger.warning("Invalid restart time from %s: empty", user.phone_number)
        return "Kripya expected restart time batayein. (Jaise: 30 mins, 1 ghanta, 2 hours)"

    context = state.context_json or {}
    investigation = {
        **context.get("driver_investigation", {}),
        "expected_restart_time": restart_time,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    updated_context = {**context, "driver_investigation": investigation}
    update_state(user.phone_number, DRIVER_INVESTIGATION, updated_context)

    summary = (
        f"Driver investigation details saved.\n"
        f"Reason: {investigation['stop_reason'].title()}\n"
        f"Location: {investigation['current_location']}\n"
        f"Need mechanic: {'Haan' if investigation['needs_mechanic'] else 'Nahi'}\n"
        f"Expected restart: {investigation['expected_restart_time']}\n\n"
        "Agar yeh conversation interrupt bhi hui ho, toh aap dobara message bhej kar continue kar sakte hain.\n"
        "Agar issue close ho gaya ho toh 'closed' bhejiye."
    )
    logger.info("Driver investigation stored for %s: %s", user.phone_number, investigation)
    
    # Notify manager about the investigation summary
    manager_phone = context.get("manager_phone")
    if manager_phone:
        manager_summary = (
            f"📋 DRIVER INVESTIGATION SUMMARY\n\n"
            f"Driver: {context.get('driver_name', 'Unknown')}\n"
            f"Vehicle: {context.get('vehicle_number', 'Unknown')}\n\n"
            f"Stop Reason: {investigation['stop_reason'].title()}\n"
            f"Current Location: {investigation['current_location']}\n"
            f"Need Mechanic: {'Yes' if investigation['needs_mechanic'] else 'No'}\n"
            f"Expected Restart: {investigation['expected_restart_time']}\n\n"
            f"Reply:\n"
            f"1. Issue resolved\n"
            f"2. Issue NOT resolved\n"
            f"3. Close alert"
        )
        send_whatsapp_message(manager_phone, manager_summary)
        # Keep manager in WAITING_MANAGER_REPLY state to handle their response
        logger.info("Manager %s notified about investigation for vehicle %s", manager_phone, context.get('vehicle_number'))
    
    return summary


def _handle_contact_driver_state(user, state, text_body: str) -> str:
    """Handle manager's follow-up options after accepting responsibility."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    # Check if this is actually a driver responding to an alert
    driver_phone = context.get("driver_phone")
    if user.phone_number == driver_phone:
        # Driver is responding to the alert - start troubleshooting
        update_state(user.phone_number, ASK_IF_DRIVING, context)
        return (
            "Dhanyavaad contact karne ke liye.\n\n"
            "Aapka vehicle 'NOT WORKING' status show kar raha hai.\n"
            "Kya aap fir se is vehicle ko chalate ho? (Haan / Nahi)"
        )

    # Manager's options after accepting responsibility
    # Option 1: Get driver investigation
    if normalized in ["1", "1.", "driver", "get driver", "driver investigation"]:
        driver_phone = context.get("driver_phone")
        
        if driver_phone:
            # Send investigation start message to driver
            investigation_prompt = _build_driver_investigation_prompt()
            send_whatsapp_message(driver_phone, investigation_prompt)
            
            # Set driver state to investigation
            set_state(driver_phone, ASK_DRIVER_STOP_REASON, context)
            
            # Update manager state to waiting for driver response
            update_state(user.phone_number, WAITING_MANAGER_REPLY, context)
            
            return (
                f"Driver ko investigation prompt bhej diya gaya hai.\n"
                f"Jab driver details provide karega, aapko summary bhej denge."
            )
        else:
            update_state(user.phone_number, CONTACT_DRIVER, context)
            return (
                "Driver ka number available nahi hai.\n"
                "Kripya driver ka phone number bhejiye."
            )

    # Option 2: Manager investigates themselves
    if normalized in ["2", "2.", "self", "myself", "khud se", "mara"]:
        update_state(user.phone_number, ASK_DRIVER_STOP_REASON, context)
        return (
            "Theek hai. Aap investigation ke saath agad badhe.\n\n"
            "Pehle bataiye - vehicle kyun ruk gaya? Options:\n"
            "1. Breakdown\n"
            "2. Maintenance\n"
            "3. Waiting Load\n"
            "4. Leave\n"
            "5. Other"
        )

    # Option 3: Contact someone else
    if normalized in ["3", "3.", "other", "contact", "kisi aur ko", "else"]:
        update_state(user.phone_number, WAITING_NEW_CONTACT_NAME, context)
        return (
            "Theek hai. Kripya us contact person ka naam batayein:\n"
            "(Jaise: Supervisor, Owner, Mechanic, etc.)"
        )

    # Invalid response - show options again
    return (
        "Kripya koi valid option chune:\n"
        "1. Driver se investigation details lena\n"
        "2. Khud se investigation karna\n"
        "3. Kisi aur ko contact karna"
    )


def _handle_waiting_manager_reply_state(user, state, text_body: str) -> str:
    """Handle manager's responses while waiting for driver investigation completion."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    # Manager marks issue as closed
    if normalized in ["close", "closed", "resolved", "done", "complete"]:
        update_state(user.phone_number, CLOSED, context)
        return "Alert closed. Dhanyavaad."

    # Manager marks issue as escalation needed
    if normalized in ["escalate", "escalation", "urgent", "critical", "emergency"]:
        update_state(user.phone_number, ESCALATION_SUPPORT_TICKET, context)
        return (
            "Issue escalated to technical support.\n"
            f"Ticket ID: TICKET_{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}\n"
            "Support team 2-4 hours mein contact karega."
        )

    # Manager requests driver investigation status
    if normalized in ["status", "update", "summary", "investigation", "progress"]:
        investigation = context.get("driver_investigation", {})
        if investigation:
            status_msg = (
                f"📋 Current Investigation Status:\n\n"
                f"Stop Reason: {investigation.get('stop_reason', 'Pending')}\n"
                f"Location: {investigation.get('current_location', 'Pending')}\n"
                f"Need Mechanic: {investigation.get('needs_mechanic', 'Pending')}\n"
                f"Expected Restart: {investigation.get('expected_restart_time', 'Pending')}\n\n"
                f"Last Updated: {investigation.get('updated_at', 'N/A')}"
            )
        else:
            status_msg = "Driver investigation abhi pending hai. Driver ka response wait kar rahe hain."
        
        update_state(user.phone_number, WAITING_MANAGER_REPLY, context)
        return status_msg

    # Default: acknowledge and stay in waiting state
    update_state(user.phone_number, WAITING_MANAGER_REPLY, context)
    return (
        "Message note kar liya gaya hai.\n"
        "Available commands:\n"
        "• 'status' - Investigation status\n"
        "• 'escalate' - Escalate to support\n"
        "• 'closed' - Close alert\n"
        "• Or send any update"
    )


def _handle_driver_investigation_state(user, state, text_body: str) -> str:
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    if normalized in ["close", "closed", "resolved", "done", "complete"]:
        update_state(user.phone_number, CLOSED, context)
        return "Driver investigation complete. Alert closed."

    if "summary" in normalized or "update" in normalized:
        update_state(user.phone_number, SUMMARY_SENT, context)
        return "Summary received. Dhanyavaad."

    update_state(user.phone_number, DRIVER_INVESTIGATION, context)
    return "Driver investigation chal rahi hai. Jab extra update ho tab bhejiye."


def _handle_summary_sent_state(user, state, text_body: str) -> str:
    normalized = _normalize_text(text_body)

    if normalized in ["close", "closed", "resolved", "done", "complete"]:
        update_state(user.phone_number, CLOSED, state.context_json or {})
        return "Alert closed. Dhanyavaad."

    return (
        "Summary already sent.\n"
        "Agar issue ab close ho gaya hai toh 'closed' likh kar bhejiye."
    )


def _handle_ask_if_driving_state(user, state, text_body: str) -> str:
    """Ask driver if currently driving the vehicle."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    if _is_affirmative(normalized):
        update_state(user.phone_number, ASK_CAN_PARK, context)
        return (
            "Kya aap vehicle ko 30 minute ke liye safe park kar sakte hain "
            "taki hum troubleshooting kar saken?\n"
            "Haan / Nahi"
        )

    if _is_negative(normalized):
        update_state(user.phone_number, ASK_TURN_ON_IGNITION, context)
        return (
            "Theek hai. Kripya ignition ON kar dijiye aur hume batayein.\n"
            "Ignition on kar diya?"
        )

    return "Kripya sirf Haan ya Nahi mein reply dein. Kya aap fir se is vehicle ko chalate ho?"


def _handle_ask_can_park_state(user, state, text_body: str) -> str:
    """Ask if driver can park vehicle for troubleshooting."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    if _is_affirmative(normalized):
        update_state(user.phone_number, ASK_TURN_ON_IGNITION, context)
        return (
            "Bahut achha. Vehicle ko park karke ignition ON kar dijiye.\n"
            "Ignition on kar diya?"
        )

    if _is_negative(normalized):
        update_state(user.phone_number, WAITING_MANAGER_REPLY, context)
        return (
            "Theek hai. Aap baad mein troubleshoot kar sakte hain.\n"
            "Abhi manager ko update kar denge."
        )

    return "Kripya sirf Haan ya Nahi mein reply dein. Kya aap vehicle park kar sakte hain?"


def _handle_ask_turn_on_ignition_state(user, state, text_body: str) -> str:
    """Confirm ignition is turned on and start troubleshooting."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    if _is_affirmative(normalized):
        update_state(user.phone_number, TROUBLESHOOT_POWER_LED, context)
        return (
            "Dhanyavaad. Ab troubleshooting shuru karte hain.\n\n"
            "STEP 1: POWER LED STATUS\n"
            "Device ke front panel ko dekiye. Power LED kaunsa colour dikhai de raha hai?\n"
            "Options:\n"
            "1. OFF (Light nahi hai)\n"
            "2. RED\n"
            "3. GREEN\n"
            "4. BLINKING\n\n"
            "Number bhejiye:"
        )

    return "Kripya sirf Haan mein reply dein. Ignition on kar dijiye."


def _handle_troubleshoot_power_led_state(user, state, text_body: str) -> str:
    """Handle Power LED status."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}
    investigation = context.get("troubleshooting", {})

    if normalized in ["1", "1.", "off"]:
        investigation["power_led"] = "OFF"
        investigation["power_issue_found"] = True
        context["troubleshooting"] = investigation
        update_state(user.phone_number, ESCALATION_SUPPORT_TICKET, context)
        return (
            "🔴 POWER SUPPLY ISSUE DETECTED\n\n"
            "Possible causes:\n"
            "✓ Battery voltage low\n"
            "✓ Fuse failure\n"
            "✓ Power wiring issue\n"
            "✓ Grounding problem\n\n"
            "Troubleshooting steps:\n"
            "1. Battery voltage check karein\n"
            "2. Fuse condition verify karein\n"
            "3. Power wiring inspect karein\n"
            "4. Grounding connection check karein\n\n"
            "Ye steps karne ke baad hume update bhejiye."
        )

    if normalized in ["2", "2.", "red"]:
        investigation["power_led"] = "RED"
        context["troubleshooting"] = investigation
        update_state(user.phone_number, TROUBLESHOOT_GSM_LED, context)
        return (
            "Theek hai. RED light indicates device is powered.\n\n"
            "STEP 2: GSM LED STATUS\n"
            "GSM LED kaunsa colour dikhai de raha hai?\n"
            "Options:\n"
            "1. OFF\n"
            "2. RED\n"
            "3. GREEN\n"
            "4. BLINKING\n\n"
            "Number bhejiye:"
        )

    if normalized in ["3", "3.", "green"]:
        investigation["power_led"] = "GREEN"
        context["troubleshooting"] = investigation
        update_state(user.phone_number, TROUBLESHOOT_GSM_LED, context)
        return (
            "Excellent! GREEN light indicates normal power.\n\n"
            "STEP 2: GSM LED STATUS\n"
            "GSM LED kaunsa colour dikhai de raha hai?\n"
            "Options:\n"
            "1. OFF\n"
            "2. RED\n"
            "3. GREEN\n"
            "4. BLINKING\n\n"
            "Number bhejiye:"
        )

    if normalized in ["4", "4.", "blinking"]:
        investigation["power_led"] = "BLINKING"
        context["troubleshooting"] = investigation
        update_state(user.phone_number, TROUBLESHOOT_GSM_LED, context)
        return (
            "Blinking light indicates normal operation.\n\n"
            "STEP 2: GSM LED STATUS\n"
            "GSM LED kaunsa colour dikhai de raha hai?\n"
            "Options:\n"
            "1. OFF\n"
            "2. RED\n"
            "3. GREEN\n"
            "4. BLINKING\n\n"
            "Number bhejiye:"
        )

    return (
        "Kripya sahi option select karein (1-4).\n"
        "Power LED kaunsa colour dikhai de raha hai?\n"
        "1. OFF\n2. RED\n3. GREEN\n4. BLINKING"
    )


def _handle_troubleshoot_gsm_led_state(user, state, text_body: str) -> str:
    """Handle GSM LED status."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}
    investigation = context.get("troubleshooting", {})

    if normalized in ["1", "1.", "off"]:
        investigation["gsm_led"] = "OFF"
        investigation["gsm_issue_found"] = True
        context["troubleshooting"] = investigation
        update_state(user.phone_number, ESCALATION_SUPPORT_TICKET, context)
        return (
            "🔴 SIM CARD / NETWORK ISSUE DETECTED\n\n"
            "Possible causes:\n"
            "✓ SIM not activated\n"
            "✓ Data balance low/zero\n"
            "✓ No network coverage\n"
            "✓ SIM slot issue\n\n"
            "Troubleshooting steps:\n"
            "1. SIM activation status check karein\n"
            "2. Data balance verify karein\n"
            "3. Network coverage check karein\n"
            "4. SIM ko remove aur reinsert karein\n\n"
            "Ye steps karne ke baad hume update bhejiye."
        )

    if normalized in ["2", "2.", "red", "3", "3.", "green", "4", "4.", "blinking"]:
        investigation["gsm_led"] = normalized if normalized in ["red", "green", "blinking"] else ["RED", "GREEN", "BLINKING"][(["2", "2.", "3", "3.", "4", "4."].index(normalized) % 3)]
        context["troubleshooting"] = investigation
        update_state(user.phone_number, TROUBLESHOOT_GPS_LED, context)
        return (
            "Theek hai. GSM connectivity okay hai.\n\n"
            "STEP 3: GPS LED STATUS\n"
            "GPS LED kaunsa colour dikhai de raha hai?\n"
            "Options:\n"
            "1. OFF\n"
            "2. SLOW BLINKING\n"
            "3. FAST BLINKING\n"
            "4. SOLID/STEADY\n\n"
            "Number bhejiye:"
        )

    return (
        "Kripya sahi option select karein (1-4).\n"
        "GSM LED kaunsa colour dikhai de raha hai?\n"
        "1. OFF\n2. RED\n3. GREEN\n4. BLINKING"
    )


def _handle_troubleshoot_gps_led_state(user, state, text_body: str) -> str:
    """Handle GPS LED status."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}
    investigation = context.get("troubleshooting", {})

    if normalized in ["1", "1.", "off"]:
        investigation["gps_led"] = "OFF"
        investigation["gps_issue_found"] = True
        context["troubleshooting"] = investigation
        update_state(user.phone_number, ESCALATION_SUPPORT_TICKET, context)
        return (
            "🔴 GPS SIGNAL ISSUE\n\n"
            "Possible causes:\n"
            "✓ Weak GPS signal\n"
            "✓ Antenna uncovered/damaged\n"
            "✓ Metal enclosure interference\n"
            "✓ Poor sky visibility\n\n"
            "Troubleshooting steps:\n"
            "1. Vehicle ko open area/sky mein le jayein\n"
            "2. GPS antenna ko check karein (uncovered hona chahiye)\n"
            "3. Metal enclosure se door karein\n"
            "4. 5-10 minutes wait karein\n\n"
            "Ye steps karne ke baad hume update bhejiye."
        )

    if normalized in ["2", "2.", "slow", "blinking slow"]:
        investigation["gps_led"] = "SLOW_BLINKING"
        context["troubleshooting"] = investigation
        update_state(user.phone_number, ASK_RESOLUTION_CONFIRMATION, context)
        return (
            "Theek hai. Slow blinking indicates GPS acquiring satellites.\n"
            "Kripya 5-10 minutes wait karein aur fir check karein.\n\n"
            "Kya ab vehicle online aa gaya hai?"
        )

    if normalized in ["3", "3.", "fast", "blinking fast"]:
        investigation["gps_led"] = "FAST_BLINKING"
        context["troubleshooting"] = investigation
        update_state(user.phone_number, ASK_RESOLUTION_CONFIRMATION, context)
        return (
            "Excellent! Fast blinking indicates GPS is acquiring signal.\n"
            "Ab thoda wait kariye...\n\n"
            "Kya ab vehicle online aa gaya hai?"
        )

    if normalized in ["4", "4.", "solid", "steady"]:
        investigation["gps_led"] = "SOLID"
        context["troubleshooting"] = investigation
        update_state(user.phone_number, ASK_RESOLUTION_CONFIRMATION, context)
        return (
            "Perfect! Solid GPS light indicates device is fully operational.\n\n"
            "Kya ab vehicle online aa gaya hai aur NOT WORKING status hataa?"
        )

    return (
        "Kripya sahi option select karein (1-4).\n"
        "GPS LED kaunsa colour dikhai de raha hai?\n"
        "1. OFF\n2. SLOW BLINKING\n3. FAST BLINKING\n4. SOLID/STEADY"
    )


def _handle_ask_resolution_confirmation_state(user, state, text_body: str) -> str:
    """Ask if issue is resolved after troubleshooting."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    # Handle numeric responses from manager summary
    if normalized in ["1", "1.", "resolved", "yes", "haan", "haa"]:
        investigation = context.get("driver_investigation", {}) or context.get("troubleshooting", {})
        investigation["resolved"] = True
        context["driver_investigation"] = investigation
        update_state(user.phone_number, SUMMARY_SENT, context)
        return (
            "🎉 BAHUT BADIYA!\n\n"
            "Issue successfully resolved!\n"
            "Alert closed.\n\n"
            "Aapke cooperation ke liye dhanyavaad.\n"
            "Agar fir se problem aa toh contact kar sakte hain."
        )

    if normalized in ["2", "2.", "unresolved", "no", "nahi", "na"]:
        investigation = context.get("driver_investigation", {}) or context.get("troubleshooting", {})
        investigation["resolved"] = False
        context["driver_investigation"] = investigation
        update_state(user.phone_number, ESCALATION_SUPPORT_TICKET, context)
        return (
            "Samajh gaya. Issue abhi bhi unresolved hai.\n\n"
            "Hum isko TECHNICAL SUPPORT TICKET mein escalate kar rahe hain.\n"
            f"Ticket ID: TICKET_{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}\n\n"
            "Technical team 2-4 hours mein contact karega."
        )
    
    if normalized in ["3", "3.", "close", "closed"]:
        update_state(user.phone_number, CLOSED, context)
        return "Alert closed. Dhanyavaad."

    return "Kripya 1, 2, ya 3 mein reply dein.\n1. Issue resolved\n2. Issue NOT resolved\n3. Close alert"


def _handle_escalation_support_ticket_state(user, state, text_body: str) -> str:
    """Handle escalation to support team."""
    normalized = _normalize_text(text_body)
    context = state.context_json or {}

    if normalized in ["close", "closed", "done"]:
        update_state(user.phone_number, CLOSED, context)
        return "Ticket closed. Dhanyavaad."

    investigation = context.get("troubleshooting", {})
    ticket_info = (
        f"Ticket Status: OPEN\n"
        f"Troubleshooting Data: {investigation}\n\n"
        f"Technical team aapko jaldi contact karega."
    )

    return ticket_info


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

    if state.current_step == FLEET_ALERT_CREATED:
        return _handle_fleet_alert_created_state(user, state, normalized, text_body)

    if state.current_step == WAITING_NEW_CONTACT_NAME:
        return _handle_waiting_new_contact_name_state(user, state, text_body)

    if state.current_step == WAITING_NEW_CONTACT_PHONE:
        return _handle_waiting_new_contact_phone_state(user, state, text_body)

    if state.current_step == WAITING_NEW_CONTACT:
        return _handle_waiting_new_contact_state(user, state, text_body)

    if state.current_step == ASK_DRIVER_STOP_REASON:
        return _handle_ask_driver_stop_reason_state(user, state, text_body)

    if state.current_step == ASK_DRIVER_LOCATION:
        return _handle_ask_driver_location_state(user, state, text_body)

    if state.current_step == ASK_NEED_MECHANIC:
        return _handle_ask_need_mechanic_state(user, state, text_body)

    if state.current_step == ASK_EXPECTED_RESTART_TIME:
        return _handle_ask_expected_restart_time_state(user, state, text_body)

    if state.current_step == CONTACT_DRIVER:
        return _handle_contact_driver_state(user, state, text_body)

    if state.current_step == WAITING_MANAGER_REPLY:
        return _handle_waiting_manager_reply_state(user, state, text_body)

    if state.current_step == DRIVER_INVESTIGATION:
        return _handle_driver_investigation_state(user, state, text_body)

    if state.current_step == SUMMARY_SENT:
        return _handle_summary_sent_state(user, state, text_body)

    if state.current_step == ASK_IF_DRIVING:
        return _handle_ask_if_driving_state(user, state, text_body)

    if state.current_step == ASK_CAN_PARK:
        return _handle_ask_can_park_state(user, state, text_body)

    if state.current_step == ASK_TURN_ON_IGNITION:
        return _handle_ask_turn_on_ignition_state(user, state, text_body)

    if state.current_step == TROUBLESHOOT_POWER_LED:
        return _handle_troubleshoot_power_led_state(user, state, text_body)

    if state.current_step == TROUBLESHOOT_GSM_LED:
        return _handle_troubleshoot_gsm_led_state(user, state, text_body)

    if state.current_step == TROUBLESHOOT_GPS_LED:
        return _handle_troubleshoot_gps_led_state(user, state, text_body)

    if state.current_step == ASK_RESOLUTION_CONFIRMATION:
        return _handle_ask_resolution_confirmation_state(user, state, text_body)

    if state.current_step == ESCALATION_SUPPORT_TICKET:
        return _handle_escalation_support_ticket_state(user, state, text_body)

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
