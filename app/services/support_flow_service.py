import logging
import re
from typing import Optional, Tuple

from app.services.greeting_service import GreetingService
from app.services.menu_service import MenuService
from app.services.state_manager import ConversationStep, StateManager
from app.services.ticket_service import create_ticket
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger("app.support_flow")


def _normalize_text(text: str) -> str:
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    return text in ["haan", "haa", "yes", "y", "h"]


def _is_negative(text: str) -> bool:
    return text in ["nahi", "na", "no", "nahin"]


def _normalize_phone_number(phone_input: str) -> Tuple[Optional[str], str]:
    """
    Normalize phone number to E.164 format for WhatsApp API.
    
    Args:
        phone_input: Raw phone number input from user
        
    Returns:
        Tuple of (normalized_number, error_message)
        If successful: ("+919876543210", "")
        If failed: (None, "error description")
    """
    if not phone_input:
        return None, "Phone number cannot be empty"
    
    # Clean the input - remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone_input.strip())
    
    # Log the cleaning process
    logger.info(
        "Phone number cleaning process",
        extra={
            "original_input": phone_input,
            "cleaned_input": cleaned
        }
    )
    
    # Check for completely invalid characters
    if not re.match(r'^[\+\d]+$', cleaned):
        return None, "Phone number contains invalid characters. Only numbers and + are allowed."
    
    # Handle different input formats
    if cleaned.startswith('+'):
        # Already has country code
        formatted_number = cleaned
    elif cleaned.startswith('91') and len(cleaned) == 12:
        # Indian number with country code but no +
        formatted_number = '+' + cleaned
    elif cleaned.startswith('0') and len(cleaned) == 11:
        # Indian number with leading 0 (remove 0 and add +91)
        formatted_number = '+91' + cleaned[1:]
    elif len(cleaned) == 10:
        # Indian number without country code
        formatted_number = '+91' + cleaned
    else:
        # Try to guess format
        if len(cleaned) >= 10 and len(cleaned) <= 15:
            # Assume Indian number if 10-15 digits and no country code
            if not cleaned.startswith('91'):
                formatted_number = '+91' + cleaned
            else:
                formatted_number = '+' + cleaned
        else:
            return None, f"Invalid phone number length: {len(cleaned)} digits. Expected 10-15 digits."
    
    # Validate E.164 format
    e164_pattern = r'^\+[1-9]\d{1,14}$'
    if not re.match(e164_pattern, formatted_number):
        return None, f"Phone number {formatted_number} is not in valid international format"
    
    # Additional validation for Indian numbers (most common case)
    if formatted_number.startswith('+91'):
        if len(formatted_number) != 13:  # +91 + 10 digits
            return None, f"Indian phone numbers must have exactly 10 digits after +91. Got: {len(formatted_number) - 3}"
        
        # Check if it's a valid Indian mobile number (starts with 6,7,8,9)
        first_digit = formatted_number[3]  # First digit after +91
        if first_digit not in '6789':
            logger.warning(
                "Potentially invalid Indian mobile number",
                extra={"phone_number": formatted_number, "first_digit": first_digit}
            )
    
    logger.info(
        "Phone number successfully normalized",
        extra={
            "original_input": phone_input,
            "normalized_number": formatted_number
        }
    )
    
    return formatted_number, ""


def _send_whatsapp_with_detailed_logging(phone_number: str, message: str, context: dict = None) -> Tuple[bool, str]:
    """
    Send WhatsApp message with comprehensive error handling and logging.
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        logger.info(
            "Attempting to send WhatsApp message",
            extra={
                "to_phone": phone_number,
                "message_length": len(message),
                "context": context or {}
            }
        )
        
        response = send_whatsapp_message(phone_number, message)
        
        # Log successful response
        logger.info(
            "WhatsApp message sent successfully",
            extra={
                "to_phone": phone_number,
                "response": response,
                "context": context or {}
            }
        )
        
        return True, ""
        
    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Failed to send WhatsApp message",
            extra={
                "to_phone": phone_number,
                "error": error_msg,
                "error_type": type(e).__name__,
                "context": context or {}
            },
            exc_info=True
        )
        
        # Categorize error types for better user feedback
        if "invalid number" in error_msg.lower():
            return False, "The phone number appears to be invalid or not registered with WhatsApp"
        elif "rate limit" in error_msg.lower():
            return False, "Message sending temporarily limited. Please try again in a few minutes"
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return False, "Network connection issue. Please try again"
        else:
            return False, f"Failed to send message: {error_msg}"


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

    # New unified flow - Ask if user is the right person
    if current_step == ConversationStep.ASK_RIGHT_PERSON.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_PROBLEM_DESCRIPTION)
            logger.info(
                "Right person confirmed",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_PROBLEM_DESCRIPTION.value},
            )
            return (
                "बढ़िया! मशीन में क्या समस्या है?\n"
                "Great! What is the problem in the machine?\n\n"
                "कृपया समस्या का विवरण दें।\n"
                "Please describe the problem."
            )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_NUMBER)
            logger.info(
                "Wrong person - asking for contact",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CONTACT_NUMBER.value},
            )
            return (
                "कोई बात नहीं। कृपया सही व्यक्ति का फोन नंबर दें जिससे हमें बात करनी चाहिए।\n"
                "No problem. Please provide the phone number of the right person we should talk to.\n\n"
                "उदाहरण / Example: 9876543210"
            )

        logger.warning(
            "Invalid right person response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )

    # Handle problem description
    if current_step == ConversationStep.ASK_PROBLEM_DESCRIPTION.value:
        state_manager.update_context(user.phone_number, {"problem_description": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.VEHICLE_NUMBER)
        logger.info(
            "Problem description received",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.VEHICLE_NUMBER.value},
        )
        return (
            "धन्यवाद। अब कृपया वाहन का नंबर बताएं।\n"
            "Thank you. Now please provide the vehicle number.\n\n"
            "उदाहरण / Example: DL01AB1234"
        )

    # Handle contact number for wrong person scenario
    if current_step == ConversationStep.ASK_CONTACT_NUMBER.value:
        contact_input = text_body.strip()
        
        logger.info(
            "Processing contact number input",
            extra={
                "original_phone": user.phone_number,
                "contact_input": contact_input
            }
        )
        
        # Validate and normalize phone number
        normalized_contact, validation_error = _normalize_phone_number(contact_input)
        
        if validation_error:
            logger.warning(
                "Invalid contact number provided",
                extra={
                    "original_phone": user.phone_number,
                    "contact_input": contact_input,
                    "validation_error": validation_error
                }
            )
            return (
                f"❌ फोन नंबर सही नहीं है: {validation_error}\n"
                f"❌ Phone number is incorrect: {validation_error}\n\n"
                "कृपया सही फोन नंबर दें। उदाहरण:\n"
                "Please provide a correct phone number. Examples:\n"
                "• 9876543210\n"
                "• +919876543210\n"
                "• 919876543210"
            )
        
        # Store the contact information
        state_manager.update_context(user.phone_number, {
            "contact_number": normalized_contact,
            "original_contact_input": contact_input
        })
        
        # Create breakdown notification message
        breakdown_message = (
            "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
            "यह मशीन टूटी हुई अवस्था में है और हमारी सहायता की आवश्यकता है।\n"
            "This machine is in breakdown state and needs our assistance.\n\n"
            "क्या आपको सहायता की आवश्यकता है?\n"
            "Do you need assistance?\n\n"
            "कृपया 'हाँ' या 'Yes' भेजकर जवाब दें।\n"
            "Please reply with 'हाँ' or 'Yes' to start support."
        )
        
        # Send breakdown notification with enhanced error handling
        success, error_message = _send_whatsapp_with_detailed_logging(
            normalized_contact, 
            breakdown_message,
            context={
                "original_user": user.phone_number,
                "contact_type": "breakdown_alert",
                "original_input": contact_input
            }
        )
        
        if success:
            # Clear conversation state after successful message
            state_manager.clear_state(user.phone_number)
            logger.info(
                "Breakdown alert successfully sent to contact person",
                extra={
                    "original_phone": user.phone_number,
                    "contact_phone": normalized_contact,
                    "original_input": contact_input
                }
            )
            
            return (
                f"✅ सफलतापूर्वक संदेश भेजा गया!\n"
                f"✅ Message sent successfully!\n\n"
                f"📱 संदेश भेजा गया: {normalized_contact}\n"
                f"📱 Message sent to: {normalized_contact}\n\n"
                "उन्हें बताया गया है कि मशीन टूटी हुई है और सहायता की जरूरत है।\n"
                "They have been informed that the machine is broken and needs assistance.\n\n"
                "वे जल्दी ही हमसे संपर्क करेंगे।\n"
                "They will contact us soon for support."
            )
        else:
            logger.error(
                "Failed to send breakdown alert to contact person",
                extra={
                    "original_phone": user.phone_number,
                    "contact_phone": normalized_contact,
                    "error": error_message,
                    "original_input": contact_input
                }
            )
            
            # Don't clear state on failure - let user try again
            return (
                f"❌ संदेश भेजने में त्रुटि: {error_message}\n"
                f"❌ Error sending message: {error_message}\n\n"
                "कृपया फिर से कोशिश करें या दूसरा नंबर दें।\n"
                "Please try again or provide a different number.\n\n"
                f"आपका दिया गया नंबर: {normalized_contact}\n"
                f"Number you provided: {normalized_contact}"
            )

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
