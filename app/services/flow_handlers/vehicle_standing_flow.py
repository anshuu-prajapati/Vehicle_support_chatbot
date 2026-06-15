"""
Vehicle Standing Flow Handler

Enhanced Flow: G | VEHICLE STANDING FLOW
Q17: Vehicle kitne samay se standing hai? (<24h / 24-48h / >48h)
  If >48 Hours → Close Case
  If <48 Hours:
    Q18: Vehicle ki current location kya hai? (Text)
    Q19: Vehicle inspection ke liye kab available hai? (Date & Time)
→ Service Request Created (if < 48 hrs)
"""
import logging
from datetime import datetime, date, time
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.flow_handlers.service_request_collector import start_service_request_collection

logger = logging.getLogger("app.vehicle_standing_flow")


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


def handle_vehicle_standing_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Vehicle Standing flow - Enhanced Flow.
    
    Flow:
    - Q17: Vehicle kitne samay se standing hai?
      - >48 hrs → Close Case
      - <48 hrs → Q18, Q19 → Service Request
    
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
    
    # Q17: Standing duration
    if current_step == ConversationStep.VEHICLE_STANDING_DURATION.value:
        duration_map = {
            "1": "Less Than 24 Hours",
            "2": "24-48 Hours",
            "3": "More Than 48 Hours"
        }
        
        duration = duration_map.get(normalized)
        if not duration:
            return (
                "⚠️ कृपया सही option चुनें।\n"
                "⚠️ Please select valid option.\n\n"
                "Q17: वाहन कितने समय से खड़ा है?\n"
                "For how long has the vehicle been standing?\n\n"
                "1️⃣ 24 घंटे से कम / Less than 24 hrs\n"
                "2️⃣ 24-48 घंटे / 24-48 hrs\n"
                "3️⃣ 48 घंटे से अधिक / More than 48 hrs"
            )
        
        state_manager.update_context(user_phone, {"standing_duration": duration})
        
        # If more than 48 hours → Close Case
        if normalized == "3":
            logger.info(f"Vehicle Standing: >48 hours - Closing case for {user_phone}")
            state_manager.clear_state(user_phone)
            return (
                "✅ समझ गए।\n"
                "✅ Understood.\n\n"
                "वाहन लंबे समय से पार्क है (>48 घंटे)।\n"
                "Vehicle has been long-parked (>48 hours).\n\n"
                "यह सामान्य है। जब वाहन फिर से उपयोग में आएगा, GPS चालू हो जाएगा।\n"
                "This is normal. GPS will work when vehicle is used again.\n\n"
                "केस बंद कर दिया गया है।\n"
                "Case has been closed.\n\n"
                "धन्यवाद! / Thank you!"
            )
        else:
            # Less than 48 hours → Ask Q18
            state_manager.set_state(user_phone, ConversationStep.VEHICLE_STANDING_LOCATION)
            return (
                "Q18: वाहन की current location क्या है?\n"
                "What is the vehicle's current location?\n\n"
                "कृपया पूरा पता दें।\n"
                "Please provide full address."
            )
    
    # Q18: Current location
    elif current_step == ConversationStep.VEHICLE_STANDING_LOCATION.value:
        if len(text_body.strip()) < 5:
            return (
                "⚠️ कृपया पूरा पता दें।\n"
                "⚠️ Please provide complete address."
            )
        
        state_manager.update_context(user_phone, {"location": text_body.strip()})
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_STANDING_INSPECTION_DATE)
        return (
            "✅ Location noted.\n\n"
            "Q19: वाहन inspection के लिए कब available है?\n"
            "When is the vehicle available for inspection?\n\n"
            "कृपया date और time दें।\n"
            "Please provide date and time.\n\n"
            "Format: DD/MM/YYYY HH:MM\n"
            "उदाहरण / Example: 16/06/2026 10:00"
        )
    
    # Q19: Inspection date & time
    elif current_step == ConversationStep.VEHICLE_STANDING_INSPECTION_DATE.value:
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
        
        logger.info(f"Vehicle Standing: <48 hours - creating service request for {user_phone}")
        state_manager.update_context(user_phone, {
            "issue_classification": "VEHICLE_STANDING",
            "inspection_date": parsed_date.isoformat(),
            "inspection_time": parsed_time.isoformat(),
            "needs_service": True
        })
        return start_service_request_collection(user_phone, state_manager, db)
    
    # Unknown step
    logger.warning(f"Unknown step in vehicle standing flow: {current_step}")
    return (
        "⚠️ कुछ गलत हो गया। कृपया 'reset' टाइप करें।\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
