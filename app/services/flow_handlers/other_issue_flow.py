"""
Other/Unknown Issue Flow Handler

Enhanced Flow: H | UNKNOWN / OTHER ISSUE FLOW
Q20: Kripya issue thoda aur detail mein batayein (Free text)
→ LLM reclassifies the issue
  If GPS Related → Route to correct Service Flow
  If Non-GPS Related → Close Case
"""
import logging
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.intent_classification_service import classify_customer_intent

logger = logging.getLogger("app.other_issue_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def handle_other_issue_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Other/Unknown Issue flow - Enhanced Flow.
    
    Flow:
    - Q20: Kripya issue thoda aur detail mein batayein
    - → LLM reclassifies
      - If GPS Related → Route to correct flow
      - If Non-GPS Related → Close Case
    
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
    
    # Q20: Issue description for reclassification
    if current_step == ConversationStep.OTHER_ISSUE_DESCRIPTION.value:
        if len(text_body.strip()) < 5:
            return (
                "⚠️ कृपया issue को विस्तार से बताएं।\n"
                "⚠️ Please describe the issue in detail."
            )
        
        # Store description
        state_manager.update_context(user_phone, {
            "issue_description": text_body.strip(),
            "customer_response": text_body.strip()
        })
        
        # Reclassify using LLM
        issue_type, method = classify_customer_intent(text_body)
        
        logger.info(
            f"Reclassified as {issue_type} using {method}",
            extra={
                "phone": user_phone,
                "issue_type": issue_type,
                "method": method,
                "description": text_body[:100]
            }
        )
        
        # Check if GPS related
        gps_related_types = [
            "GPS_REMOVED",
            "GPS_DAMAGED",
            "VEHICLE_RUNNING",
            "VEHICLE_STANDING",
            "BATTERY_DISCONNECT",
            "WORKSHOP",
            "ACCIDENT"
        ]
        
        if issue_type in gps_related_types:
            # GPS Related → Route to correct flow
            from app.services.service_engineer_flow_service import _route_to_flow_handler
            
            logger.info(f"Other flow: GPS related - routing to {issue_type} flow for {user_phone}")
            state_manager.update_context(user_phone, {
                "issue_classification": issue_type,
                "reclassified": True
            })
            
            return _route_to_flow_handler(user_phone, issue_type, state_manager, db)
        else:
            # Non-GPS Related → Close Case
            logger.info(f"Other flow: Non-GPS related - closing case for {user_phone}")
            state_manager.clear_state(user_phone)
            return (
                "समझ गए। यह issue GPS से related नहीं लगता।\n"
                "Understood. This issue does not seem GPS-related.\n\n"
                "कृपया सही department से संपर्क करें।\n"
                "Please contact the appropriate department.\n\n"
                "केस बंद कर दिया गया है।\n"
                "Case has been closed.\n\n"
                "धन्यवाद! / Thank you!"
            )
    
    # Unknown step
    logger.warning(f"Unknown step in other issue flow: {current_step}")
    return (
        "⚠️ कुछ गलत हो गया। कृपया 'reset' टाइप करें।\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )
