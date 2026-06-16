"""
Accident Flow Handler

Flow:
Customer selects: 2️⃣ Accident
Q1: Vehicle workshop mein hai? (LLM-driven)
  - YES → Q2: Expected date → Close Case
  - NO → Q3: Vehicle operational hai? (LLM-driven)
    - YES → Route to Vehicle Running Flow
    - NO → Manual Review
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


def _is_vehicle_in_workshop(text: str) -> bool:
    """
    Check if vehicle is in workshop/repair center using LLM understanding.
    Returns True if vehicle is in workshop/repair.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for simple affirmative responses
    simple_yes = ["haan", "haa", "yes", "y", "h", "ji", "ji haan"]
    if normalized in simple_yes:
        return True
    
    # Quick check for simple negative responses
    simple_no = ["nahi", "na", "no", "nahin", "n"]
    if normalized in simple_no:
        return False
    
    # Use LLM for natural language understanding
    try:
        prompt = f"""Determine if the vehicle is currently in a workshop/repair center.

User was asked: "Kya vehicle filhaal accident ke baad workshop ya repair center mein hai?"

User replied: "{text}"

Examples of YES (vehicle in workshop):
- "haan workshop mein hai"
- "service center mein hai"
- "repair chal rahi hai"
- "body work chal raha hai"
- "insurance claim ke liye khadi hai"
- "garage mein hai"
- "accident ke baad workshop mein khadi hai"

Examples of NO (vehicle not in workshop):
- "nahi"
- "workshop mein nahi hai"
- "road par hai"
- "vehicle chal rahi hai"
- "ghar par khadi hai"

Respond with ONLY ONE WORD: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM workshop check for accident: '{text[:50]}' -> {response}")
        
        return response == "YES"
        
    except Exception as e:
        logger.error(f"LLM workshop check failed: {str(e)}")
        # Fallback to keyword matching
        workshop_keywords = ["workshop", "garage", "service center", "repair", "body work", "insurance"]
        return any(keyword in normalized for keyword in workshop_keywords)


def _is_vehicle_operational(text: str) -> bool:
    """
    Check if vehicle is operational/running using LLM understanding.
    Returns True if vehicle is operational.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for simple affirmative responses
    simple_yes = ["haan", "haa", "yes", "y", "h", "ji", "chal rahi"]
    if any(word in normalized for word in simple_yes):
        return True
    
    # Quick check for simple negative responses
    simple_no = ["nahi", "na", "no", "nahin", "khadi", "damage"]
    if normalized in ["nahi", "na", "no", "nahin"]:
        return False
    
    # Use LLM for natural language understanding
    try:
        prompt = f"""Determine if the vehicle is operational (working/running).

User was asked: "Kya vehicle abhi operational condition mein hai aur chal rahi hai?"

User replied: "{text}"

Examples of YES (vehicle is operational):
- "haan chal rahi hai"
- "driver gaadi chala raha hai"
- "vehicle operational hai"
- "thik hai chal rahi hai"
- "yes working"

Examples of NO (vehicle not operational):
- "nahi chal rahi"
- "bahut damage hai"
- "khadi hai"
- "abhi use nahi ho sakti"
- "not working"

Respond with ONLY ONE WORD: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM operational check: '{text[:50]}' -> {response}")
        
        return response == "YES"
        
    except Exception as e:
        logger.error(f"LLM operational check failed: {str(e)}")
        # Fallback to keyword matching
        operational_keywords = ["chal rahi", "operational", "running", "chala raha", "working"]
        not_operational_keywords = ["nahi", "khadi", "damage", "not working"]
        
        has_operational = any(keyword in normalized for keyword in operational_keywords)
        has_not_operational = any(keyword in normalized for keyword in not_operational_keywords)
        
        if has_not_operational:
            return False
        return has_operational


# Accident sub-steps stored in context
ACCIDENT_WORKSHOP_CHECK = "ACCIDENT_WORKSHOP_CHECK"
ACCIDENT_EXPECTED_DATE = "ACCIDENT_EXPECTED_DATE"
ACCIDENT_OPERATIONAL_CHECK = "ACCIDENT_OPERATIONAL_CHECK"


def handle_accident_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Accident flow with LLM-driven conversational understanding.
    
    Flow:
    Q1: Vehicle workshop mein hai? (LLM understands response)
      - YES → Q2: Expected date → Close case
      - NO → Q3: Vehicle operational hai?
        - YES → Route to Vehicle Running Flow
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
    context = state_manager.get_context(user_phone)
    accident_sub_step = context.get("accident_sub_step")
    
    logger.info(
        f"Accident Flow: Processing message",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": accident_sub_step,
            "message_preview": text_body[:50]
        }
    )
    
    if current_step == ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION.value:
        
        # Q2: Expected date (after YES to workshop question)
        if accident_sub_step == ACCIDENT_EXPECTED_DATE:
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
                f"Expected availability date: 📅 {expected_date_str}\n\n"
                "Is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                "Agar vehicle operational hone ke baad bhi GPS issue rahta hai, to aap support request raise kar sakte hain.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: Closed"
            )
        
        # Q3: Vehicle operational check (after NO to workshop question)
        if accident_sub_step == ACCIDENT_OPERATIONAL_CHECK:
            if _is_vehicle_operational(text_body):
                # Vehicle is operational - route to Vehicle Running Flow
                logger.info(f"Accident: Vehicle operational - routing to Vehicle Running Flow for {user_phone}")
                
                # Update classification
                state_manager.update_context(user_phone, {
                    "issue_classification": "VEHICLE_RUNNING",
                    "reclassified_from": "ACCIDENT",
                    "accident_sub_step": None
                })
                
                # Route to Vehicle Running Flow
                from app.services.service_engineer_flow_service import _route_to_flow_handler
                return _route_to_flow_handler(user_phone, "VEHICLE_RUNNING", state_manager, db)
            
            else:
                # Vehicle is NOT operational - Manual Review
                logger.info(f"Accident: Vehicle not operational - manual review for {user_phone}")
                
                # Store final data
                state_manager.update_context(user_phone, {
                    "case_status": "MANUAL_REVIEW",
                    "review_reason": "Accident - Vehicle not operational, not in workshop"
                })
                
                # Clear state (conversation complete)
                state_manager.clear_state(user_phone)
                
                return (
                    "Dhanyavaad.\n\n"
                    "Humari team is case ko review karegi aur zarurat padne par aapse sampark karegi.\n\n"
                    "Case Status: Manual Review"
                )
        
        # Q1: Initial workshop check (LLM-driven understanding)
        if _is_vehicle_in_workshop(text_body):
            # Vehicle is in workshop - ask for expected date
            logger.info(f"Accident: Vehicle in workshop (LLM confirmed) - asking expected date for {user_phone}")
            state_manager.update_context(user_phone, {"accident_sub_step": ACCIDENT_EXPECTED_DATE})
            
            return (
                "Vehicle ke dobara operational hone ki expected date kya hai?\n\n"
                "Example: 20-06-2026"
            )
        
        else:
            # Vehicle is NOT in workshop - ask if operational
            logger.info(f"Accident: Vehicle not in workshop (LLM confirmed) - asking operational status for {user_phone}")
            state_manager.update_context(user_phone, {"accident_sub_step": ACCIDENT_OPERATIONAL_CHECK})
            
            return "Kya vehicle abhi operational condition mein hai aur chal rahi hai?"
    
    # Unknown step
    logger.warning(f"Unknown step in accident flow: {current_step}")
    return (
        "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein.\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
