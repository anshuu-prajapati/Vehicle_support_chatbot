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
from app.services.clarification_handler import (
    should_clarify,
    generate_clarification_response,
    get_context_explanation_for_step,
    get_current_question_text
)

logger = logging.getLogger("app.workshop_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """
    Check if response is affirmative using LLM-driven understanding.
    Returns True if the text indicates YES/confirmation.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for simple yes responses
    simple_yes = ["haan", "haa", "yes", "y", "h", "1", "हाँ", "हां", "ji", "ji haan"]
    if normalized in simple_yes:
        return True
    
    # If it's a simple no, return False quickly
    simple_no = ["nahi", "na", "no", "nahin", "n", "2", "नहीं"]
    if normalized in simple_no:
        return False
    
    # Use LLM for natural language understanding
    try:
        prompt = f"""Determine if this response means YES/AFFIRMATIVE or NO/NEGATIVE.

User was asked: "Kya vehicle filhaal workshop ya service center mein hai?"

User replied: "{text}"

Examples of YES:
- "haan"
- "yes"
- "repair ke liye rakhi hai"
- "service center mein khadi hai"
- "workshop mein hai"
- "garage mein hai"
- "haan workshop mein hai"

Examples of NO:
- "nahi"
- "no"
- "workshop mein nahi hai"
- "nahi khadi nahi hai"

Respond with ONLY ONE WORD: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM affirmative check: '{text[:50]}' -> {response}")
        
        return response == "YES"
        
    except Exception as e:
        logger.error(f"LLM affirmative check failed: {str(e)}")
        # Fallback to keyword matching
        affirmative_keywords = ["workshop", "garage", "service center", "repair", "maintenance", "haan", "yes", "hai"]
        return any(keyword in normalized for keyword in affirmative_keywords)


def _is_negative(text: str) -> bool:
    """
    Check if response is negative using LLM-driven understanding.
    Returns True if the text indicates NO/rejection.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for simple no responses
    simple_no = ["nahi", "na", "no", "nahin", "n", "2", "नहीं"]
    if normalized in simple_no:
        return True
    
    # If it's a simple yes, return False quickly
    simple_yes = ["haan", "haa", "yes", "y", "h", "1", "हाँ", "हां", "ji", "ji haan"]
    if normalized in simple_yes:
        return False
    
    # Use LLM for natural language understanding
    try:
        prompt = f"""Determine if this response means YES/AFFIRMATIVE or NO/NEGATIVE.

User was asked: "Kya vehicle filhaal workshop ya service center mein hai?"

User replied: "{text}"

Examples of YES:
- "haan"
- "yes"
- "repair ke liye rakhi hai"
- "service center mein khadi hai"

Examples of NO:
- "nahi"
- "no"
- "workshop mein nahi hai"
- "road par hai"
- "khadi hai bahar"

Respond with ONLY ONE WORD: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM negative check: '{text[:50]}' -> {response}")
        
        return response == "NO"
        
    except Exception as e:
        logger.error(f"LLM negative check failed: {str(e)}")
        # Fallback to keyword matching
        negative_keywords = ["nahi", "no", "not", "नहीं"]
        return any(keyword in normalized for keyword in negative_keywords)


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
    Handle Workshop flow - directly asks for expected operational date.
    
    Flow:
    Q1: Expected date when vehicle will be operational → Close case
    
    Args:
        user_phone: User's phone number
        text_body: User's message
        current_step: Current conversation step
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        Response message
    """
    logger.info(
        f"Workshop Flow: Processing message",
        extra={
            "phone": user_phone,
            "step": current_step,
            "message_preview": text_body[:50]
        }
    )
    
    # Check if user needs clarification
    if should_clarify(text_body):
        logger.info(f"Workshop: User needs clarification")
        
        context_explanation = (
            "Hum pooch rahe hain ki vehicle workshop se kab operational hoga "
            "taaki hum record mein note kar sakein."
        )
        current_question = "Vehicle ke dobara operational hone ki expected date kya hai?"
        
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    
    # Q1: Expected date when vehicle will be operational
    if current_step == ConversationStep.WORKSHOP_CONFIRMATION.value:
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
            "Humne note kar liya hai ki vehicle filhaal workshop mein hai.\n\n"
            f"Expected availability date: 📅 {expected_date_str}\n\n"
            "Is samay kisi service engineer ki avashyakta nahi hai.\n\n"
            "Agar vehicle operational hone ke baad bhi GPS issue rahta hai, to aap support request raise kar sakte hain.\n\n"
            "🙏 Thank You\n\n"
            "Case Status: Closed"
        )
    
    # Unknown step
    logger.warning(f"Unknown step in workshop flow: {current_step}")
    return (
        "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein.\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
