"""
Vehicle Running (No GPS Data) Flow Handler

Enhanced Flow: F | VEHICLE RUNNING — NO GPS DATA FLOW
Q13: Driver ka naam kya hai? (Text)
Q14: Driver ka mobile number kya hai? (Text)
Q15: Vehicle ki current location kya hai? (Text)
Q16: Vehicle inspection ke liye kab available hai? (Date & Time)
→ Service Request Created
"""
import logging
from datetime import datetime, date, time
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.flow_handlers.service_request_collector import start_service_request_collection

logger = logging.getLogger("app.vehicle_running_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


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


def handle_vehicle_running_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Vehicle Running (No GPS Data) flow - Enhanced Flow.
    
    Flow:
    - Q13: Driver ka naam kya hai?
    - Q14: Driver ka mobile number kya hai?
    - Q15: Vehicle ki current location kya hai?
    - Q16: Vehicle inspection ke liye kab available hai?
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
    
    # Q13: Driver name
    if current_step == ConversationStep.VEHICLE_RUNNING_DRIVER_NAME.value:
        if len(text_body.strip()) < 2:
            return (
                "⚠️ कृपया ड्राइवर का नाम बताएं।\n"
                "⚠️ Please provide driver's name."
            )
        
        state_manager.update_context(user_phone, {"driver_name": text_body.strip()})
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_RUNNING_DRIVER_MOBILE)
        return (
            "✅ Driver name noted.\n\n"
            "Q14: ड्राइवर का mobile number क्या है?\n"
            "What is the driver's mobile number?\n\n"
            "उदाहरण / Example: +919876543210"
        )
    
    # Q14: Driver mobile
    elif current_step == ConversationStep.VEHICLE_RUNNING_DRIVER_MOBILE.value:
        if not _validate_phone(text_body):
            return (
                "⚠️ कृपया सही mobile number दें।\n"
                "⚠️ Please provide valid mobile number.\n\n"
                "उदाहरण / Example: +919876543210 या 9876543210"
            )
        
        state_manager.update_context(user_phone, {"driver_mobile": text_body.strip()})
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_RUNNING_LOCATION)
        return (
            "✅ Mobile number noted.\n\n"
            "Q15: वाहन की current location क्या है?\n"
            "What is the vehicle's current location?\n\n"
            "कृपया पूरा पता दें।\n"
            "Please provide full address."
        )
    
    # Q15: Current location
    elif current_step == ConversationStep.VEHICLE_RUNNING_LOCATION.value:
        if len(text_body.strip()) < 5:
            return (
                "⚠️ कृपया पूरा पता दें।\n"
                "⚠️ Please provide complete address."
            )
        
        state_manager.update_context(user_phone, {"location": text_body.strip()})
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_RUNNING_INSPECTION_DATE)
        return (
            "✅ Location noted.\n\n"
            "Q16: वाहन inspection के लिए कब available है?\n"
            "When is the vehicle available for inspection?\n\n"
            "कृपया date और time दें।\n"
            "Please provide date and time.\n\n"
            "Format: DD/MM/YYYY HH:MM\n"
            "उदाहरण / Example: 16/06/2026 10:00"
        )
    
    # Q16: Inspection date & time
    elif current_step == ConversationStep.VEHICLE_RUNNING_INSPECTION_DATE.value:
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
        
        logger.info(f"Vehicle Running: All info collected - creating service request for {user_phone}")
        state_manager.update_context(user_phone, {
            "issue_classification": "VEHICLE_RUNNING",
            "inspection_date": parsed_date.isoformat(),
            "inspection_time": parsed_time.isoformat(),
            "needs_service": True
        })
        return start_service_request_collection(user_phone, state_manager, db)
    
    # Unknown step
    logger.warning(f"Unknown step in vehicle running flow: {current_step}")
    return (
        "⚠️ कुछ गलत हो गया। कृपया 'reset' टाइप करें।\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
