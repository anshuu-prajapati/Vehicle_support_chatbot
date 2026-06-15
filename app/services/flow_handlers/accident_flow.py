"""
Accident Flow Handler

Flow:
Customer selects: 2️⃣ Accident
Q1: Expected date → Close Case
"""
import logging
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep

logger = logging.getLogger("app.accident_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


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


# Accident sub-step stored in context
ACCIDENT_EXPECTED_DATE = "ACCIDENT_EXPECTED_DATE"


def handle_accident_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Accident flow.
    
    Flow:
    Q1: Expected date → Close case
    
    Args:
        user_phone: User's phone number
        text_body: User's message
        current_step: Current conversation step
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        Response message
    """
    
    # Q1: Expected date (direct entry after selecting Accident)
    if current_step == ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION.value:
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
        
        logger.info(f"Accident: Case closed with expected date {expected_date_str} for {user_phone}")
        
        # Store final data
        state_manager.update_context(user_phone, {
            "accident_expected_date": expected_date_str,
            "case_status": "CLOSED"
        })
        
        # Clear state (conversation complete)
        state_manager.clear_state(user_phone)
        
        return (
            "✅ Dhanyavaad.\n\n"
            "Humne note kar liya hai ki vehicle accident ke baad repair process mein hai.\n\n"
            f"Expected availability date: 📅 *{expected_date_str}*\n\n"
            "Is wajah se GPS inactive hona expected hai aur is samay kisi service engineer ki avashyakta nahi hai.\n\n"
            "Agar vehicle dobara operational hone ke baad bhi GPS issue rahta hai, to aap support request raise kar sakte hain.\n\n"
            "Hum hamesha aapki sahayata ke liye uplabdh hain.\n\n"
            "🙏 Thank You\n\n"
            "Case Status: *Closed*"
        )
    
    # Unknown step
    logger.warning(f"Unknown step in accident flow: {current_step}")
    return (
        "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein.\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
