"""
GPS Removed Flow Handler

Enhanced Flow: D | GPS REMOVED FLOW
Q5: GPS ko dobara install kab karwana hai? (Date & Time)
Q6: Vehicle ki current location kya hai? (Text)
Q7: Vehicle owner ka contact number confirm karein (Text)
Q8: Vehicle available rahegi? (Yes/No)
  If NO → Q9: Vehicle kab available hogi? (Date & Time)
→ Service Request Created
"""
import logging
from datetime import datetime, date, time
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.flow_handlers.service_request_collector import start_service_request_collection

logger = logging.getLogger("app.gps_removed_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """Check if response is affirmative"""
    return text in ["haan", "haa", "yes", "y", "h", "1", "हाँ", "हां"]


def _is_negative(text: str) -> bool:
    """Check if response is negative"""
    return text in ["nahi", "na", "no", "nahin", "n", "2", "नहीं"]


def _validate_date_time(text: str) -> tuple:
    """Validate and parse date/time from text"""
    try:
        # Try DD/MM/YYYY HH:MM format
        dt = datetime.strptime(text.strip(), "%d/%m/%Y %H:%M")
        return dt.date(), dt.time()
    except ValueError:
        try:
            # Try DD-MM-YYYY HH:MM
            dt = datetime.strptime(text.strip(), "%d-%m-%Y %H:%M")
            return dt.date(), dt.time()
        except ValueError:
            return None, None


def _validate_phone(phone: str) -> bool:
    """Validate phone number"""
    import re
    cleaned = re.sub(r'[^\d+]', '', phone)
    return len(cleaned) >= 10 and len(cleaned) <= 15


def handle_gps_removed_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle GPS Removed flow - Enhanced Flow.
    
    Flow:
    - Q5: GPS ko dobara install kab karwana hai?
    - Q6: Vehicle ki current location kya hai?
    - Q7: Vehicle owner ka contact number confirm karein
    - Q8: Vehicle available rahegi?
    - Q9: Vehicle kab available hogi? (if Q8 = NO)
    - → Service Request
    
    Args:
        user_phone: User's phone number
        text_body: User's message
        current_step: Current conversation step
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        Response message
    """
    normalized = _normalize_text(text_body)
    
    # Q5: Reinstallation date & time
    if current_step == ConversationStep.GPS_REMOVED_REINSTALL_DATE.value:
        parsed_date, parsed_time = _validate_date_time(text_body)
        
        if not parsed_date or not parsed_time:
            return (
                "⚠️ कृपया सही format में date और time दें।\n"
                "⚠️ Please provide date and time in correct format.\n\n"
                "Format: DD/MM/YYYY HH:MM\n"
                "उदाहरण / Example: 16/06/2026 10:00"
            )
        
        # Check if date is not in the past
        if parsed_date < date.today():
            return (
                "⚠️ पुरानी तारीख नहीं चुन सकते।\n"
                "⚠️ Cannot select past date.\n\n"
                "कृपया आज या भविष्य की तारीख दें।\n"
                "Please provide today or future date."
            )
        
        state_manager.update_context(user_phone, {
            "reinstallation_date": parsed_date.isoformat(),
            "reinstallation_time": parsed_time.isoformat()
        })
        state_manager.set_state(user_phone, ConversationStep.GPS_REMOVED_LOCATION)
        return (
            "✅ Date और time noted.\n\n"
            "Q6: वाहन की वर्तमान लोकेशन क्या है?\n"
            "What is the vehicle's current location?\n\n"
            "कृपया पूरा पता दें।\n"
            "Please provide full address."
        )
    
    # Q6: Current location
    elif current_step == ConversationStep.GPS_REMOVED_LOCATION.value:
        if len(text_body.strip()) < 5:
            return (
                "⚠️ कृपया पूरा पता दें।\n"
                "⚠️ Please provide complete address."
            )
        
        state_manager.update_context(user_phone, {"location": text_body.strip()})
        state_manager.set_state(user_phone, ConversationStep.GPS_REMOVED_CONTACT)
        return (
            "✅ Location noted.\n\n"
            "Q7: वाहन मालिक का contact number confirm करें।\n"
            "Please confirm vehicle owner's contact number.\n\n"
            "उदाहरण / Example: +919876543210"
        )
    
    # Q7: Owner contact
    elif current_step == ConversationStep.GPS_REMOVED_CONTACT.value:
        if not _validate_phone(text_body):
            return (
                "⚠️ कृपया सही mobile number दें।\n"
                "⚠️ Please provide valid mobile number.\n\n"
                "उदाहरण / Example: +919876543210 या 9876543210"
            )
        
        state_manager.update_context(user_phone, {"owner_mobile": text_body.strip()})
        state_manager.set_state(user_phone, ConversationStep.GPS_REMOVED_AVAILABILITY)
        return (
            "✅ Contact noted.\n\n"
            "Q8: क्या वाहन available रहेगी?\n"
            "Will the vehicle be available?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )
    
    # Q8: Vehicle availability
    elif current_step == ConversationStep.GPS_REMOVED_AVAILABILITY.value:
        if _is_affirmative(normalized):
            # Yes - Vehicle available
            logger.info(f"GPS Removed: Vehicle available - creating service request for {user_phone}")
            state_manager.update_context(user_phone, {
                "issue_classification": "GPS_REMOVED",
                "vehicle_available": True,
                "needs_service": True
            })
            return start_service_request_collection(user_phone, state_manager, db)
        elif _is_negative(normalized):
            # No - Ask when available (Q9)
            state_manager.set_state(user_phone, ConversationStep.GPS_REMOVED_AVAILABLE_DATE)
            return (
                "Q9: वाहन कब available होगी?\n"
                "When will the vehicle be available?\n\n"
                "कृपया date और time दें।\n"
                "Please provide date and time.\n\n"
                "Format: DD/MM/YYYY HH:MM\n"
                "उदाहरण / Example: 17/06/2026 14:00"
            )
        else:
            return (
                "⚠️ कृपया 1 (हाँ) या 2 (नहीं) चुनें।\n"
                "⚠️ Please select 1 (Yes) or 2 (No)."
            )
    
    # Q9: When available (if Q8 = NO)
    elif current_step == ConversationStep.GPS_REMOVED_AVAILABLE_DATE.value:
        parsed_date, parsed_time = _validate_date_time(text_body)
        
        if not parsed_date or not parsed_time:
            return (
                "⚠️ कृपया सही format में date और time दें।\n"
                "⚠️ Please provide date and time in correct format.\n\n"
                "Format: DD/MM/YYYY HH:MM\n"
                "उदाहरण / Example: 17/06/2026 14:00"
            )
        
        if parsed_date < date.today():
            return (
                "⚠️ पुरानी तारीख नहीं चुन सकते।\n"
                "⚠️ Cannot select past date."
            )
        
        logger.info(f"GPS Removed: Vehicle available later - creating service request for {user_phone}")
        state_manager.update_context(user_phone, {
            "issue_classification": "GPS_REMOVED",
            "vehicle_available": False,
            "vehicle_available_date": parsed_date.isoformat(),
            "vehicle_available_time": parsed_time.isoformat(),
            "needs_service": True
        })
        return start_service_request_collection(user_phone, state_manager, db)
    
    # Unknown step
    logger.warning(f"Unknown step in GPS removed flow: {current_step}")
    return (
        "⚠️ कुछ गलत हो गया। कृपया 'reset' टाइप करें।\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
