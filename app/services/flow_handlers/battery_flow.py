"""
Battery Disconnect Flow Handler

Enhanced Flow: C | BATTERY DISCONNECT FLOW
Q4: Kya battery maintenance ya replacement ke liye disconnect ki gayi hai?
- YES → Close Case
- NO → Manual Review
"""
import logging
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep

logger = logging.getLogger("app.battery_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """Check if response is affirmative"""
    return text in ["haan", "haa", "yes", "y", "h", "1", "हाँ", "हां"]


def _is_negative(text: str) -> bool:
    """Check if response is negative"""
    return text in ["nahi", "na", "no", "nahin", "n", "2", "नहीं"]


def handle_battery_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Battery Disconnect flow - Enhanced Flow.
    
    Flow:
    - Q4: Kya battery maintenance ya replacement ke liye disconnect ki gayi hai?
      - YES → Close Case
      - NO → Manual Review
    
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
    
    # Q4: Battery maintenance confirmation
    if current_step == ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION.value:
        if _is_affirmative(normalized):
            # YES - Close Case
            logger.info(f"Battery flow: YES - Closing case for {user_phone}")
            state_manager.clear_state(user_phone)
            return (
                "✅ समझ गए।\n"
                "✅ Understood.\n\n"
                "जब बैटरी दोबारा लगा दी जाएगी, GPS अपने आप काम करने लगेगा।\n"
                "GPS will work automatically when battery is reconnected.\n\n"
                "केस बंद कर दिया गया है।\n"
                "Case has been closed.\n\n"
                "धन्यवाद! / Thank you!"
            )
        elif _is_negative(normalized):
            # NO - Manual Review
            logger.info(f"Battery flow: NO - Manual Review for {user_phone}")
            state_manager.clear_state(user_phone)
            return (
                "ठीक है। हमारी टीम इस मामले की जांच करेगी।\n"
                "Okay. Our team will review this case.\n\n"
                "हम जल्द ही आपसे संपर्क करेंगे।\n"
                "We will contact you soon.\n\n"
                "धन्यवाद! / Thank you!"
            )
        else:
            return (
                "⚠️ कृपया 1 (हाँ) या 2 (नहीं) चुनें।\n"
                "⚠️ Please select 1 (Yes) or 2 (No)."
            )
    
    # Unknown step
    logger.warning(f"Unknown step in battery flow: {current_step}")
    return (
        "⚠️ कुछ गलत हो गया। कृपया 'reset' टाइप करें।\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
