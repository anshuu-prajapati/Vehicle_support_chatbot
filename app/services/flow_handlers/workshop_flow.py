"""
Workshop Flow Handler

Flow:
Customer selects: 1️⃣ Workshop / Service Center
Q1: Kya vehicle workshop mein hai? (Yes/No)
  - YES → Q2: Expected date → Close Case
  - NO → Show 7 other options → Route to selected flow
"""
import logging
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep

logger = logging.getLogger("app.workshop_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """Check if response is affirmative"""
    return text in ["haan", "haa", "yes", "y", "h", "1", "हाँ", "हां"]


def _is_negative(text: str) -> bool:
    """Check if response is negative"""
    return text in ["nahi", "na", "no", "nahin", "n", "2", "नहीं"]


def _validate_date(date_str: str) -> tuple:
    """
    Validate and parse date in DD-MM-YYYY format.
    Returns (parsed_date, None) if valid, (None, error_message) if invalid.
    """
    try:
        # Try DD-MM-YYYY format
        parsed = datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
        return parsed, None
    except ValueError:
        try:
            # Try DD/MM/YYYY format
            parsed = datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
            return parsed, None
        except ValueError:
            return None, "Invalid date format. Please use DD-MM-YYYY (Example: 20-06-2026)"


# Workshop sub-step stored in context
WORKSHOP_EXPECTED_DATE = "WORKSHOP_EXPECTED_DATE"
WORKSHOP_RESELECT = "WORKSHOP_RESELECT"


def handle_workshop_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Workshop flow.
    
    Flow:
    Q1: Kya vehicle workshop mein hai? (Yes/No)
      - YES → Q2: Expected date → Close
      - NO → Show 7 options → Route to selected
    
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
    context = state_manager.get_context(user_phone)
    
    # Q1: Workshop confirmation
    if current_step == ConversationStep.WORKSHOP_CONFIRMATION.value:
        workshop_sub_step = context.get("workshop_sub_step")
        
        # Handle reselection after NO
        if workshop_sub_step == WORKSHOP_RESELECT:
            # User selected one of 7 options
            option_map = {
                "1": "ACCIDENT",
                "2": "BATTERY_DISCONNECT",
                "3": "GPS_REMOVED",
                "4": "GPS_DAMAGED",
                "5": "VEHICLE_RUNNING",
                "6": "VEHICLE_STANDING",
                "7": "UNKNOWN"
            }
            
            new_issue_type = option_map.get(normalized)
            if not new_issue_type:
                return (
                    "⚠️ Kripya 1-7 ke beech ek option select karein.\n\n"
                    "1️⃣ Accident\n"
                    "2️⃣ Battery Disconnect\n"
                    "3️⃣ GPS Removed\n"
                    "4️⃣ GPS Damaged\n"
                    "5️⃣ Vehicle Running but GPS Not Updating\n"
                    "6️⃣ Vehicle Standing\n"
                    "7️⃣ Other"
                )
            
            logger.info(f"Workshop: Reselected to {new_issue_type} for {user_phone}")
            
            # Update context with new selection
            state_manager.update_context(user_phone, {
                "issue_classification": new_issue_type,
                "reclassified_from": "WORKSHOP",
                "workshop_sub_step": None
            })
            
            # Route to new flow
            from app.services.service_engineer_flow_service import _route_to_flow_handler
            return _route_to_flow_handler(user_phone, new_issue_type, state_manager, db)
        
        # Handle expected date input
        if workshop_sub_step == WORKSHOP_EXPECTED_DATE:
            parsed_date, error = _validate_date(text_body)
            
            if error:
                return f"⚠️ {error}"
            
            # Check if date is not in the past
            if parsed_date < date.today():
                return (
                    "⚠️ Purani date nahi select kar sakte.\n"
                    "Kripya aaj ya future ki date dein.\n\n"
                    "Example: 20-06-2026"
                )
            
            # Format date for display
            expected_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"Workshop: Case closed with expected date {expected_date_str} for {user_phone}")
            
            # Store final data
            state_manager.update_context(user_phone, {
                "workshop_expected_date": expected_date_str,
                "case_status": "CLOSED"
            })
            
            # Clear state (conversation complete)
            state_manager.clear_state(user_phone)
            
            return (
                "✅ Dhanyavaad.\n\n"
                "Humne note kar liya hai ki vehicle filhaal workshop/service center mein hai.\n\n"
                f"Expected availability date: 📅 *{expected_date_str}*\n\n"
                "Is wajah se GPS inactive hona expected hai aur is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                "Agar vehicle dobara chalu hone ke baad bhi GPS issue rahta hai, to aap support request raise kar sakte hain.\n\n"
                "Hum hamesha aapki sahayata ke liye uplabdh hain.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: *Closed*"
            )
        
        # Initial workshop confirmation (YES/NO)
        if _is_affirmative(normalized):
            # Ask for expected date
            logger.info(f"Workshop: YES - asking expected date for {user_phone}")
            state_manager.update_context(user_phone, {"workshop_sub_step": WORKSHOP_EXPECTED_DATE})
            return (
                "Dhanyavaad. 🙏\n\n"
                "Kripya vehicle ke dobara chalu hone ya workshop se bahar aane ki expected date batayein.\n\n"
                "📅 Expected Date: (Example: 20-06-2026)"
            )
        
        elif _is_negative(normalized):
            # Not in workshop - show 7 other options
            logger.info(f"Workshop: NO - showing other options for {user_phone}")
            state_manager.update_context(user_phone, {"workshop_sub_step": WORKSHOP_RESELECT})
            return (
                "Dhanyavaad.\n\n"
                "Aisa lagta hai ki vehicle workshop mein nahi hai.\n\n"
                "Kripya GPS inactive hone ka sahi reason select karein:\n\n"
                "1️⃣ Accident\n"
                "2️⃣ Battery Disconnect\n"
                "3️⃣ GPS Removed\n"
                "4️⃣ GPS Damaged\n"
                "5️⃣ Vehicle Running but GPS Not Updating\n"
                "6️⃣ Vehicle Standing\n"
                "7️⃣ Other"
            )
        
        else:
            # Invalid response
            return (
                "⚠️ Kripya valid option select karein.\n\n"
                "Kya vehicle filhaal workshop ya service center mein hai?\n\n"
                "1️⃣ Yes\n"
                "2️⃣ No"
            )
    
    # Unknown step
    logger.warning(f"Unknown step in workshop flow: {current_step}")
    return (
        "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein.\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
