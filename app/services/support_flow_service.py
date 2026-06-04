import logging
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.services.greeting_service import GreetingService
from app.services.menu_service import MenuService
from app.services.state_manager import ConversationStep, StateManager
from app.services.ticket_service import create_ticket
from app.services.whatsapp_service import send_whatsapp_message
from app.db.models.vehicle import Vehicle
from app.db.models.user import User

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


def _get_company_name_for_user(user_phone: str, db: Session) -> str:
    """
    Get company name for a user based on their associated vehicle.
    
    Args:
        user_phone: User's phone number
        db: Database session
        
    Returns:
        Company name or default company name
    """
    try:
        # First, get the user
        user = db.query(User).filter(User.phone_number == user_phone).first()
        if not user:
            logger.warning(f"User not found for phone: {user_phone}")
            return "Tech Solutions Pvt Ltd"
        
        # Find vehicle associated with this user (as manager, supervisor, or driver)
        vehicle = db.query(Vehicle).filter(
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


def handle_support_message(user, text_body: str, state_manager: StateManager, db: Session = None) -> str:
    normalized = _normalize_text(text_body)
    greeting_service = GreetingService(state_manager)
    menu_service = MenuService(state_manager, db)

    # Handle greetings - always show welcome menu
    if greeting_service.is_greeting(normalized):
        logger.info(
            "User entered greeting",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)

    # Get current state (state might have been reset in webhook if this is greeting/menu selection)
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

    # Handle menu selection (1 or 2) - this ensures deterministic behavior
    if current_step == ConversationStep.MAIN_MENU.value:
        # Special case: If user presses "1" and they were contacted as a driver or supervisor for GPS repair
        if normalized == "1" and context.get("contact_type") in ["driver", "supervisor"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_NEAR_VEHICLE)
            logger.info(
                f"{context.get('contact_type', 'contact')} pressed 1 for GPS repair - starting GPS troubleshooting",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value}
            )
            return (
                "GPS सिस्टम को ठीक करने के लिए हमें आपकी मदद चाहिए।\n"
                "We need your help to fix the GPS system.\n\n"
                "क्या आप वाहन के पास हैं?\n"
                "Are you near the vehicle?\n\n"
                "1️⃣ हाँ / Yes\n"
                "2️⃣ नहीं / No"
            )
        
        logger.info(
            "Processing menu selection in MAIN_MENU state",
            extra={"phone_number": user.phone_number, "text": text_body}
        )
        return menu_service.handle_menu_selection(user.phone_number, text_body)

    # New unified flow - Ask if user is the manager of specific company
    if current_step == ConversationStep.ASK_RIGHT_PERSON.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CAN_PROVIDE_OTHER_NUMBER)
            logger.info(
                "Right person confirmed - asking for other number",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CAN_PROVIDE_OTHER_NUMBER.value},
            )
            return (
                "बढ़िया! क्या हमें आपके साथ ही जारी रखना चाहिए या किसी और से बात करनी चाहिए?\n"
                "Great! Should we continue with you or should we talk with somebody else?\n\n"
                "1️⃣ मेरे साथ जारी रखें / Continue with me\n"
                "2️⃣ किसी और से बात करें / Talk with someone else"
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
        
        # Get company name for this user and show the proper message
        company_name = _get_company_name_for_user(user.phone_number, db) if db else "Tech Solutions Pvt Ltd"
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            f"क्या हम {company_name} के मैनेजर से बात कर रहे हैं?\n"
            f"Are we talking to the manager of {company_name}?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )

    # Handle if manager can provide other number
    if current_step == ConversationStep.ASK_CAN_PROVIDE_OTHER_NUMBER.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa", "continue", "मेरे साथ"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_NEAR_VEHICLE)
            logger.info(
                "Manager wants to continue with themselves - starting GPS repair flow",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value},
            )
            return (
                "GPS सिस्टम को ठीक करने के लिए हमें आपकी मदद चाहिए।\n"
                "We need your help to fix the GPS system.\n\n"
                "क्या आप वाहन के पास हैं?\n"
                "Are you near the vehicle?\n\n"
                "1️⃣ हाँ / Yes\n"
                "2️⃣ नहीं / No"
            )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin", "someone else", "किसी और"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_TYPE)
            logger.info(
                "Manager wants to talk with someone else - asking contact type with driver info",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CONTACT_TYPE.value},
            )
            
            # Get driver number from database for this user's vehicle
            driver_number = "Not available"
            if db:
                try:
                    # First, get the user
                    manager = db.query(User).filter(User.phone_number == user.phone_number).first()
                    if manager:
                        # Find vehicle where this user is manager
                        vehicle = db.query(Vehicle).filter(Vehicle.manager_id == manager.id).first()
                        if vehicle and vehicle.driver_id:
                            # Get driver details
                            driver = db.query(User).filter(User.id == vehicle.driver_id).first()
                            if driver and driver.phone_number:
                                driver_number = driver.phone_number
                                logger.info(f"Found driver number {driver_number} for manager {user.phone_number}")
                except Exception as e:
                    logger.error(f"Error fetching driver number: {str(e)}")
            
            return (
                "क्या हमें सुपरवाइजर या ड्राइवर से संपर्क करना चाहिए?\n"
                "Should we contact supervisor or driver?\n\n"
                "1️⃣ सुपरवाइजर / Supervisor\n"
                f"2️⃣ ड्राइवर / Driver whose number is {driver_number}"
            )

        logger.warning(
            "Invalid continue or someone else response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या हमें आपके साथ ही जारी रखना चाहिए या किसी और से बात करनी चाहिए?\n"
            "Should we continue with you or should we talk with somebody else?\n\n"
            "1️⃣ मेरे साथ जारी रखें / Continue with me\n"
            "2️⃣ किसी और से बात करें / Talk with someone else"
        )

    # Handle contact type selection
    if current_step == ConversationStep.ASK_CONTACT_TYPE.value:
        if normalized in ["1", "supervisor", "सुपरवाइजर"]:
            state_manager.update_context(user.phone_number, {"contact_type": "supervisor"})
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_NUMBER)
            logger.info(
                "Contact type selected: supervisor",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CONTACT_NUMBER.value},
            )
            return (
                "सुपरवाइजर का फोन नंबर दें।\n"
                "Please provide supervisor's phone number.\n\n"
                "उदाहरण / Example: 9876543210"
            )

        if normalized in ["2", "driver", "ड्राइवर"]:
            # Use driver number from database
            driver_number = None
            if db:
                try:
                    # Get the manager user
                    manager = db.query(User).filter(User.phone_number == user.phone_number).first()
                    if manager:
                        # Find vehicle where this user is manager
                        vehicle = db.query(Vehicle).filter(Vehicle.manager_id == manager.id).first()
                        if vehicle and vehicle.driver_id:
                            # Get driver details
                            driver = db.query(User).filter(User.id == vehicle.driver_id).first()
                            if driver and driver.phone_number:
                                driver_number = driver.phone_number
                                logger.info(f"Using driver number {driver_number} from database")
                except Exception as e:
                    logger.error(f"Error fetching driver number for contact: {str(e)}")
            
            if driver_number:
                # Directly proceed to send message to driver using database number
                state_manager.update_context(user.phone_number, {
                    "contact_type": "driver",
                    "contact_number": driver_number,
                    "original_contact_input": driver_number
                })
                
                # Create driver message
                breakdown_message = (
                    "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                    "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                    "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                    "आप ड्राइवर हैं। कृपया सहायता के लिए 1 दबाएं।\n"
                    "You are the driver. Please press 1 for assistance.\n\n"
                    "1️⃣ Press 1 for AI assistance"
                )
                
                # Send message to driver
                success, error_message = _send_whatsapp_with_detailed_logging(
                    driver_number, 
                    breakdown_message,
                    context={
                        "original_user": user.phone_number,
                        "contact_type": "driver",
                        "original_input": "database_driver"
                    }
                )
                
                if success:
                    # Pre-create conversation state for the driver
                    contact_state_manager = StateManager(db) if db else state_manager
                    contact_state_manager.set_state(
                        driver_number,
                        ConversationStep.MAIN_MENU,
                        context_json={"contact_type": "driver", "alert_received": True}
                    )
                    
                    # Clear original user's conversation state
                    state_manager.clear_state(user.phone_number)
                    logger.info(
                        "Driver alert sent successfully using database number",
                        extra={
                            "original_phone": user.phone_number,
                            "driver_phone": driver_number
                        }
                    )
                    
                    return (
                        f"✅ सफलतापूर्वक संदेश भेजा गया!\n"
                        f"✅ Message sent successfully!\n\n"
                        f"📱 संदेश भेजा गया (ड्राइवर / Driver): {driver_number}\n"
                        f"📱 Message sent to (Driver): {driver_number}\n\n"
                        "उन्हें बताया गया है कि GPS में समस्या है और सहायता की जरूरत है।\n"
                        "They have been informed that there are GPS issues and assistance is needed.\n\n"
                        "वे जल्दी ही हमसे संपर्क करेंगे।\n"
                        "They will contact us soon for support."
                    )
                else:
                    logger.error(
                        "Failed to send driver alert using database number",
                        extra={
                            "original_phone": user.phone_number,
                            "driver_phone": driver_number,
                            "error": error_message
                        }
                    )
                    return (
                        f"❌ ड्राइवर को संदेश भेजने में त्रुटि: {error_message}\n"
                        f"❌ Error sending message to driver: {error_message}\n\n"
                        f"ड्राइवर का नंबर: {driver_number}\n"
                        f"Driver's number: {driver_number}\n\n"
                        "कृपया बाद में कोशिश करें।\n"
                        "Please try again later."
                    )
            else:
                # No driver number found, ask for manual input
                state_manager.update_context(user.phone_number, {"contact_type": "driver"})
                state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_NUMBER)
                logger.warning(
                    "No driver number found in database, asking for manual input",
                    extra={"phone_number": user.phone_number}
                )
                return (
                    "ड्राइवर का नंबर डेटाबेस में नहीं मिला। कृपया ड्राइवर का फोन नंबर दें।\n"
                    "Driver number not found in database. Please provide driver's phone number.\n\n"
                    "उदाहरण / Example: 9876543210"
                )

        logger.warning(
            "Invalid contact type response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        
        # Get driver number again for error message
        driver_number = "Not available"
        if db:
            try:
                manager = db.query(User).filter(User.phone_number == user.phone_number).first()
                if manager:
                    vehicle = db.query(Vehicle).filter(Vehicle.manager_id == manager.id).first()
                    if vehicle and vehicle.driver_id:
                        driver = db.query(User).filter(User.id == vehicle.driver_id).first()
                        if driver and driver.phone_number:
                            driver_number = driver.phone_number
            except Exception as e:
                logger.error(f"Error fetching driver number for error message: {str(e)}")
        
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या हमें सुपरवाइजर या ड्राइवर से संपर्क करना चाहिए?\n"
            "Should we contact supervisor or driver?\n\n"
            "1️⃣ सुपरवाइजर / Supervisor\n"
            f"2️⃣ ड्राइवर / Driver whose number is {driver_number}"
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

    # Handle contact number for wrong person scenario OR for supervisor/driver
    if current_step == ConversationStep.ASK_CONTACT_NUMBER.value:
        contact_input = text_body.strip()
        context = state_manager.get_context(user.phone_number)
        contact_type = context.get("contact_type", "manager")  # Default to manager for backward compatibility
        
        logger.info(
            "Processing contact number input",
            extra={
                "original_phone": user.phone_number,
                "contact_input": contact_input,
                "contact_type": contact_type
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
                    "validation_error": validation_error,
                    "contact_type": contact_type
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
            "original_contact_input": contact_input,
            "contact_type": contact_type
        })
        
        # Create appropriate message based on contact type
        if contact_type == "supervisor":
            breakdown_message = (
                "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                "आप सुपरवाइजर हैं। कृपया सहायता के लिए 1 दबाएं।\n"
                "You are the supervisor. Please press 1 for assistance.\n\n"
                "1️⃣ Press 1 for AI assistance"
            )
        elif contact_type == "driver":
            breakdown_message = (
                "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                "आप ड्राइवर हैं। कृपया सहायता के लिए 1 दबाएं।\n"
                "You are the driver. Please press 1 for assistance.\n\n"
                "1️⃣ Press 1 for AI assistance"
            )
        else:
            # Default message for manager/other contacts (backward compatibility)
            breakdown_message = (
                "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                "हम आपकी सहायता के लिए यहाँ हैं।\n"
                "We are here to help you.\n\n"
                "1️⃣ Press 1 for AI assistance"
            )
        
        # Send breakdown notification with enhanced error handling
        success, error_message = _send_whatsapp_with_detailed_logging(
            normalized_contact, 
            breakdown_message,
            context={
                "original_user": user.phone_number,
                "contact_type": contact_type,
                "original_input": contact_input
            }
        )
        
        if success:
            # Pre-create conversation state for the contact person with appropriate context
            contact_state_manager = StateManager(db) if db else state_manager
            contact_state_manager.set_state(
                normalized_contact,
                ConversationStep.MAIN_MENU,
                context_json={"contact_type": contact_type, "alert_received": True}
            )
            
            # Clear original user's conversation state after successful message
            state_manager.clear_state(user.phone_number)
            logger.info(
                "Breakdown alert successfully sent to contact person with pre-created state",
                extra={
                    "original_phone": user.phone_number,
                    "contact_phone": normalized_contact,
                    "contact_type": contact_type,
                    "original_input": contact_input
                }
            )
            
            contact_type_display = {
                "supervisor": "सुपरवाइजर / Supervisor",
                "driver": "ड्राइवर / Driver", 
                "manager": "मैनेजर / Manager"
            }.get(contact_type, contact_type)
            
            return (
                f"✅ सफलतापूर्वक संदेश भेजा गया!\n"
                f"✅ Message sent successfully!\n\n"
                f"📱 संदेश भेजा गया ({contact_type_display}): {normalized_contact}\n"
                f"📱 Message sent to ({contact_type_display}): {normalized_contact}\n\n"
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
                    "contact_type": contact_type,
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

    # GPS Repair Flow - Ask if driver is near vehicle
    if current_step == ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_IGNITION)
            logger.info(
                "Driver is near vehicle - asking to turn on ignition",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_IGNITION.value},
            )
            return (
                "बहुत अच्छा! अब वाहन की इग्निशन ऑन करें।\n"
                "Great! Now turn on the vehicle ignition.\n\n"
                "इग्निशन ऑन करने के बाद '1' दबाएं।\n"
                "Press '1' after turning on the ignition.\n\n"
                "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
            )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_SCHEDULE_CALLBACK)
            logger.info(
                "Driver is not near vehicle - asking for callback schedule",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_SCHEDULE_CALLBACK.value},
            )
            return (
                "कोई बात नहीं। क्या आप वाहन के पास जा सकते हैं या हमें बताएं कि हमें आपको कब वापस कॉल करना चाहिए?\n"
                "No problem. Can you go close to the vehicle or tell us when we should contact you back?\n\n"
                "1️⃣ मैं वाहन के पास जा सकता हूं / I can go to the vehicle\n"
                "2️⃣ बाद में कॉल करें / Call back later"
            )

        logger.warning(
            "Invalid near vehicle response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या आप वाहन के पास हैं?\n"
            "Are you near the vehicle?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )

    # GPS Repair Flow - Handle ignition confirmation
    if current_step == ConversationStep.GPS_REPAIR_IGNITION.value:
        if normalized in ["1", "done", "ignition on", "ok"]:
            # Clear state as GPS repair process is complete for now
            state_manager.clear_state(user.phone_number)
            logger.info(
                "GPS repair ignition step completed",
                extra={"phone_number": user.phone_number}
            )
            return (
                "बहुत बढ़िया! इग्निशन ऑन करने के बाद GPS सिस्टम को काम करना शुरू कर देना चाहिए।\n"
                "Excellent! After turning on the ignition, the GPS system should start working.\n\n"
                "कृपया 2-3 मिनट इंतजार करें और फिर चेक करें कि GPS सिग्नल आ रहा है या नहीं।\n"
                "Please wait 2-3 minutes and then check if GPS signal is working.\n\n"
                "अगर फिर भी समस्या है तो हमें बताएं।\n"
                "If there are still issues, please let us know.\n\n"
                "धन्यवाद! / Thank you!"
            )

        logger.warning(
            "Invalid ignition response - expecting confirmation",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया इग्निशन ऑन करने के बाद '1' दबाएं।\n"
            "Please press '1' after turning on the ignition.\n\n"
            "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
        )

    # GPS Repair Flow - Handle callback scheduling
    if current_step == ConversationStep.GPS_REPAIR_SCHEDULE_CALLBACK.value:
        if normalized in ["1", "go to vehicle", "जा सकता"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_IGNITION)
            logger.info(
                "Driver will go to vehicle - proceeding to ignition step",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_IGNITION.value},
            )
            return (
                "बहुत अच्छा! वाहन के पास जाकर इग्निशन ऑन करें।\n"
                "Great! Go to the vehicle and turn on the ignition.\n\n"
                "इग्निशन ऑन करने के बाद '1' दबाएं।\n"
                "Press '1' after turning on the ignition.\n\n"
                "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
            )

        if normalized in ["2", "call later", "बाद में"]:
            # Clear state and schedule callback (in real implementation, this could store callback time)
            state_manager.clear_state(user.phone_number)
            logger.info(
                "Driver requested callback later",
                extra={"phone_number": user.phone_number}
            )
            return (
                "ठीक है। हम आपको बाद में कॉल करेंगे।\n"
                "Okay. We will call you back later.\n\n"
                "कृपया बताएं कि हमें कितने घंटे बाद कॉल करना चाहिए? (जैसे: 1 घंटे बाद, 2 घंटे बाद)\n"
                "Please tell us how many hours later we should call? (Example: after 1 hour, after 2 hours)\n\n"
                "या आप जब वाहन के पास हों तो हमें कॉल कर सकते हैं।\n"
                "Or you can call us when you are near the vehicle."
            )

        logger.warning(
            "Invalid callback scheduling response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "1️⃣ मैं वाहन के पास जा सकता हूं / I can go to the vehicle\n"
            "2️⃣ बाद में कॉल करें / Call back later"
        )

    # Continue with existing diagnostic flow states
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

    # Default fallback - show main menu
    logger.debug("Transitioning unknown state %s to MAIN_MENU", current_step)
    greeting_service.route_to_main_menu(user.phone_number)
    return greeting_service.send_welcome(user.name)
