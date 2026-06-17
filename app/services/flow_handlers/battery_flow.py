"""
Battery Disconnect Flow Handler

Flow:
Customer selects: 3️⃣ Battery Disconnect
Q1: Battery maintenance ke liye disconnect ki gayi hai? (LLM-driven)
  - YES → Q2: Expected date → Close Case
  - NO → Ask to describe situation → Reclassify and route
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

logger = logging.getLogger("app.battery_flow")


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


def _is_battery_maintenance(text: str) -> bool:
    """
    Check if battery is disconnected for maintenance/replacement/repair using LLM understanding.
    Returns True if battery maintenance is the reason.
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
        prompt = f"""Determine if the battery is disconnected for maintenance/replacement/repair.

User was asked: "Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?"

User replied: "{text}"

Examples of YES (battery maintenance):
- "haan"
- "maintenance ke liye nikali hai"
- "battery change ho rahi hai"
- "replacement chal raha hai"
- "repair ke liye disconnect ki hai"
- "battery nikali hui hai maintenance ke liye"
- "battery change kar rahe hain"

Examples of NO (not battery maintenance):
- "nahi"
- "battery nahi nikali"
- "maintenance nahi chal rahi"
- "battery disconnect nahi hai"
- "galti se select ho gaya"
- "wrong option"

Respond with ONLY ONE WORD: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM battery maintenance check: '{text[:50]}' -> {response}")
        
        return response == "YES"
        
    except Exception as e:
        logger.error(f"LLM battery maintenance check failed: {str(e)}")
        # Fallback to keyword matching
        maintenance_keywords = ["maintenance", "replacement", "repair", "change", "nikali", "disconnect"]
        not_keywords = ["nahi", "no", "not", "galti"]
        
        has_maintenance = any(keyword in normalized for keyword in maintenance_keywords)
        has_not = any(keyword in normalized for keyword in not_keywords)
        
        if has_not:
            return False
        return has_maintenance


# Battery sub-steps stored in context
BATTERY_EXPECTED_DATE = "BATTERY_EXPECTED_DATE"
BATTERY_DESCRIBE_SITUATION = "BATTERY_DESCRIBE_SITUATION"


def handle_battery_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Battery Disconnect flow with LLM-driven conversational understanding.
    
    Flow:
    Q1: Battery maintenance ke liye disconnect ki gayi hai? (LLM understands response)
      - YES → Q2: Expected date → Close case
      - NO → Ask to describe situation → Reclassify and route
    
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
    battery_sub_step = context.get("battery_sub_step")
    
    logger.info(
        f"Battery Flow: Processing message",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": battery_sub_step,
            "message_preview": text_body[:50]
        }
    )
    
    # Check if user needs clarification
    if should_clarify(text_body):
        logger.info(f"Battery: User needs clarification at sub_step {battery_sub_step}")
        
        context_explanation = get_context_explanation_for_step(current_step, battery_sub_step)
        current_question = get_current_question_text(current_step, battery_sub_step)
        
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    
    if current_step == ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION.value:
        
        # Q2: Expected date (after YES to battery maintenance)
        if battery_sub_step == BATTERY_EXPECTED_DATE:
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
            
            logger.info(f"Battery: Case closed with expected date {expected_date_str} for {user_phone}")
            
            # Store final data
            state_manager.update_context(user_phone, {
                "battery_expected_date": expected_date_str,
                "case_status": "CLOSED"
            })
            
            # Clear state (conversation complete)
            state_manager.clear_state(user_phone)
            
            return (
                "✅ Dhanyavaad.\n\n"
                "Humne note kar liya hai ki battery maintenance/replacement ke kaaran vehicle inactive hai.\n\n"
                f"Expected availability date: 📅 {expected_date_str}\n\n"
                "Is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                "Agar battery reconnect hone ke baad bhi GPS issue rahta hai, to aap support request raise kar sakte hain.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: Closed"
            )
        
        # Q3: Reclassification (after NO to battery maintenance)
        if battery_sub_step == BATTERY_DESCRIBE_SITUATION:
            # User is describing the actual situation
            # Use LLM to reclassify
            from app.services.intent_classification_service import classify_customer_intent
            
            logger.info(f"Battery: Reclassifying from description: '{text_body[:50]}' for {user_phone}")
            
            new_issue_type, method = classify_customer_intent(text_body)
            
            logger.info(f"Battery reclassification: '{text_body}' -> {new_issue_type} using {method}")
            
            # Update context with new classification
            state_manager.update_context(user_phone, {
                "issue_classification": new_issue_type,
                "reclassified_from": "BATTERY_DISCONNECT",
                "battery_sub_step": None
            })
            
            # Route to the correct flow
            from app.services.service_engineer_flow_service import _route_to_flow_handler
            return _route_to_flow_handler(user_phone, new_issue_type, state_manager, db)
        
        # Q1: Initial battery maintenance confirmation (LLM-driven understanding)
        if _is_battery_maintenance(text_body):
            # User confirmed battery is disconnected for maintenance
            logger.info(f"Battery: YES (LLM confirmed) - asking expected date for {user_phone}")
            state_manager.update_context(user_phone, {"battery_sub_step": BATTERY_EXPECTED_DATE})
            
            return (
                "Vehicle ya battery system dobara kab operational hoga?\n\n"
                "Example: 20-06-2026"
            )
        
        else:
            # Battery maintenance is NOT the issue - ask user to describe situation
            logger.info(f"Battery: NO (LLM confirmed) - asking for situation description for {user_phone}")
            state_manager.update_context(user_phone, {"battery_sub_step": BATTERY_DESCRIBE_SITUATION})
            
            return (
                "Dhanyavaad. 🙏\n\n"
                "Aisa lagta hai ki battery disconnect issue nahi hai.\n\n"
                "Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai."
            )
    
    # Unknown step
    logger.warning(f"Unknown step in battery flow: {current_step}")
    return (
        "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein.\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
