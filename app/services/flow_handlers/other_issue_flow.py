"""
Other/Unknown Issue Flow Handler - AI Clarification Flow

This flow acts as an intelligent AI clarification system that:
1. Tries to understand the actual issue first
2. Reclassifies and routes to appropriate flows when possible
3. Creates service requests for GPS-related technical issues
4. Handles non-GPS cases appropriately
5. Does NOT immediately create tickets or close cases without understanding
"""
import logging
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.intent_classification_service import classify_customer_intent
from app.services.clarification_handler import should_clarify, generate_clarification_response

logger = logging.getLogger("app.other_issue_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_still_dont_know(text: str) -> bool:
    """
    Check if user still doesn't know the answer.
    Returns True if user says they don't have information.
    """
    normalized = _normalize_text(text)
    
    dont_know_keywords = [
        "pata nahi", "nahi pata", "malum nahi", "not sure", "no idea",
        "cant say", "can't say", "dont know", "don't know",
        "driver se puchna", "incharge se puchna", "batana padega",
        "information nahi", "mujhe nahi pata", "confirm nahi kar sakta"
    ]
    
    return any(keyword in normalized for keyword in dont_know_keywords)


def _validate_phone(phone: str) -> bool:
    """Validate phone number"""
    import re
    cleaned = re.sub(r'[^\d+]', '', phone)
    return len(cleaned) >= 10 and len(cleaned) <= 15


def _analyze_issue_with_llm(text: str) -> dict:
    """
    Use LLM to deeply analyze the issue and determine routing.
    
    Returns dict with:
        - category: GPS_RELATED, NON_GPS, NEEDS_CLARIFICATION
        - reclassify_to: Specific issue type if can be reclassified
        - requires_service: True/False
        - reasoning: Why this classification was made
    """
    from app.ai.groq_llm import generate_response
    
    try:
        prompt = f"""Analyze this customer's GPS/vehicle issue and determine the appropriate action.

Customer said: "{text}"

Analyze:
1. Is this GPS-related or not?
2. Can it be classified into a specific category?
3. Does it require service engineer visit?

Categories:
- WORKSHOP: Vehicle in workshop/service center
- ACCIDENT: Vehicle accident happened
- BATTERY_DISCONNECT: Battery disconnected for maintenance
- GPS_REMOVED: GPS removed for maintenance/repair
- GPS_DAMAGED: GPS device physically damaged/broken
- VEHICLE_RUNNING: Vehicle running but GPS not updating
- VEHICLE_STANDING: Vehicle parked/standing/not in use
- GPS_TECHNICAL: GPS-related technical issue (signal, SIM, light, device not responding)
- NON_GPS: Vehicle sold, scrapped, removed from fleet, not GPS issue

Examples:

"GPS toot gaya hai" → GPS_DAMAGED, Requires service
"Vehicle workshop mein hai" → WORKSHOP, No service needed
"Battery nikali hui hai" → BATTERY_DISCONNECT, No service needed
"Tracker light blink nahi kar rahi" → GPS_TECHNICAL, Requires service
"GPS signal nahi aa raha" → GPS_TECHNICAL, Requires service
"Vehicle bech di hai" → NON_GPS, No service needed
"SIM band hai" → GPS_TECHNICAL, Requires service
"Device chori ho gaya" → GPS_TECHNICAL, Requires service (theft case)
"Vehicle doosre city mein hai" → VEHICLE_STANDING, May need clarification
"Ignition issue hai" → NON_GPS, Not GPS related

Respond in EXACTLY this format:
CATEGORY: <GPS_RELATED|NON_GPS>
RECLASSIFY_TO: <category or NONE>
REQUIRES_SERVICE: <YES|NO>
REASONING: <brief explanation>"""

        response = generate_response(prompt).strip()
        
        logger.info(f"LLM issue analysis: '{text[:50]}' -> {response[:200]}")
        
        # Parse response
        result = {
            "category": "NEEDS_CLARIFICATION",
            "reclassify_to": None,
            "requires_service": False,
            "reasoning": "Could not parse LLM response"
        }
        
        for line in response.split('\n'):
            if line.startswith('CATEGORY:'):
                category = line.replace('CATEGORY:', '').strip()
                result["category"] = category
            elif line.startswith('RECLASSIFY_TO:'):
                reclassify = line.replace('RECLASSIFY_TO:', '').strip()
                if reclassify != "NONE":
                    result["reclassify_to"] = reclassify
            elif line.startswith('REQUIRES_SERVICE:'):
                requires = line.replace('REQUIRES_SERVICE:', '').strip()
                result["requires_service"] = requires == "YES"
            elif line.startswith('REASONING:'):
                reasoning = line.replace('REASONING:', '').strip()
                result["reasoning"] = reasoning
        
        return result
        
    except Exception as e:
        logger.error(f"LLM issue analysis failed: {str(e)}")
        return {
            "category": "NEEDS_CLARIFICATION",
            "reclassify_to": None,
            "requires_service": False,
            "reasoning": f"Analysis error: {str(e)}"
        }


def handle_other_issue_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Other/Unknown Issue flow - AI Clarification Flow.
    
    Flow:
    1. Ask user to describe issue
    2. Analyze with LLM
    3. Route to appropriate flow or action:
       - Reclassifiable → Route to specific flow
       - GPS Technical Issue → Create service request
       - Non-GPS → Manual review / Close case
    
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
        f"Other Flow: Processing message",
        extra={
            "phone": user_phone,
            "step": current_step,
            "message_preview": text_body[:50]
        }
    )
    
    # Check if user needs clarification
    if should_clarify(text_body):
        logger.info(f"Other: User needs clarification")
        
        context_explanation = (
            "Hum pooch rahe hain ki vehicle ya GPS ke saath exactly kya issue aa raha hai "
            "taaki hum aapko sahi tarike se help kar sakein."
        )
        current_question = "Vehicle ya GPS ke saath kya issue aa raha hai?"
        
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    
    # Main issue description and analysis
    if current_step == ConversationStep.OTHER_ISSUE_DESCRIPTION.value:
        if len(text_body.strip()) < 5:
            return "⚠️ Kripya issue ko thoda detail mein bataiye."
        
        # Check if user still doesn't know the issue
        if _is_still_dont_know(text_body):
            logger.info(f"Other: User still doesn't know - asking for alternate contact")
            
            state_manager.update_context(user_phone, {
                "other_sub_step": "ALTERNATE_CONTACT",
                "reason": "USER_DOESNT_KNOW"
            })
            
            return (
                "Thik hai. 🙏\n\n"
                "Kya aap driver ya vehicle incharge ka contact number share kar sakte hain?\n\n"
                "Hum unse sampark karne ki koshish karenge."
            )
        
        # Store description
        state_manager.update_context(user_phone, {
            "issue_description": text_body.strip(),
            "customer_response": text_body.strip()
        })
        
        logger.info(f"Other: Analyzing issue: '{text_body[:100]}' for {user_phone}")
        
        # Deep analysis with LLM
        analysis = _analyze_issue_with_llm(text_body)
        
        logger.info(
            f"Other: Analysis result",
            extra={
                "phone": user_phone,
                "category": analysis["category"],
                "reclassify_to": analysis["reclassify_to"],
                "requires_service": analysis["requires_service"],
                "reasoning": analysis["reasoning"]
            }
        )
        
        # Path 1: Can be reclassified to a specific flow
        if analysis["reclassify_to"]:
            from app.services.service_engineer_flow_service import _route_to_flow_handler
            
            logger.info(f"Other: Reclassifying to {analysis['reclassify_to']} for {user_phone}")
            
            state_manager.update_context(user_phone, {
                "issue_classification": analysis["reclassify_to"],
                "reclassified": True,
                "original_classification": "OTHER"
            })
            
            return _route_to_flow_handler(user_phone, analysis["reclassify_to"], state_manager, db)
        
        # Path 2: GPS-related technical issue requiring service
        if analysis["category"] == "GPS_RELATED" and analysis["requires_service"]:
            logger.info(f"Other: GPS technical issue - starting service request for {user_phone}")
            
            # Store as GPS Technical Issue
            state_manager.update_context(user_phone, {
                "issue_type": "GPS_TECHNICAL_ISSUE",
                "other_sub_step": "LOCATION"
            })
            
            return (
                "Dhanyavaad. 🙏\n\n"
                "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
                "📍 Example: Kirti Nagar, Delhi"
            )
        
        # Path 3: Non-GPS issue (vehicle sold, scrapped, etc.)
        if analysis["category"] == "NON_GPS":
            logger.info(f"Other: Non-GPS issue - manual review for {user_phone}")
            
            state_manager.update_context(user_phone, {
                "case_status": "MANUAL_REVIEW",
                "issue_category": "NON_GPS"
            })
            
            state_manager.clear_state(user_phone)
            
            return (
                "Dhanyavaad.\n\n"
                "Humne aapki jankari note kar li hai.\n\n"
                "Humari team is case ko review karegi aur zarurat padne par aapse sampark karegi.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: Manual Review"
            )
        
        # Path 4: Needs more clarification (fallback)
        logger.info(f"Other: Needs clarification - asking follow-up for {user_phone}")
        
        # Try basic intent classification as fallback
        issue_type, method = classify_customer_intent(text_body)
        
        if issue_type != "UNKNOWN":
            from app.services.service_engineer_flow_service import _route_to_flow_handler
            
            logger.info(f"Other: Fallback classification to {issue_type} for {user_phone}")
            
            state_manager.update_context(user_phone, {
                "issue_classification": issue_type,
                "reclassified": True
            })
            
            return _route_to_flow_handler(user_phone, issue_type, state_manager, db)
        
        # Still unclear - ask for GPS-related service
        return (
            "Dhanyavaad.\n\n"
            "Kya aap GPS device ki inspection karwana chahte hain?\n\n"
            "Agar haan, to vehicle ki current location bataiye."
        )
    
    # Handle location collection for GPS Technical Issue
    context = state_manager.get_context(user_phone)
    other_sub_step = context.get("other_sub_step")
    
    if other_sub_step == "LOCATION":
        if len(text_body.strip()) < 5:
            return "⚠️ Kripya pura address dein."
        
        logger.info(f"Other: Location received, creating service request for {user_phone}")
        
        # Import service request creation
        from app.services.ticket_service import create_service_request_ticket
        from app.db.models.user import User
        from app.db.models.vehicle import Vehicle
        
        # Get vehicle number
        vehicle_number = context.get("vehicle_number")
        if not vehicle_number:
            try:
                user = db.query(User).filter(User.phone_number == user_phone).first()
                if user:
                    vehicle = db.query(Vehicle).filter(
                        (Vehicle.manager_id == user.id) |
                        (Vehicle.supervisor_id == user.id) |
                        (Vehicle.driver_id == user.id)
                    ).first()
                    if vehicle:
                        vehicle_number = vehicle.vehicle_number
            except Exception as e:
                logger.error(f"Error getting vehicle number: {str(e)}")
        
        if not vehicle_number:
            vehicle_number = "UNKNOWN"
        
        # Create service request
        try:
            issue_description = context.get("issue_description", "GPS Technical Issue")
            
            ticket = create_service_request_ticket(
                vehicle_number=vehicle_number,
                issue_type="GPS_TECHNICAL_ISSUE",
                customer_phone=user_phone,
                location=text_body.strip(),
                owner_mobile=user_phone,
                driver_name=issue_description[:100]  # Store issue description
            )
            
            if ticket:
                ticket_number = ticket.ticket_number
                logger.info(f"Other: Service request created - {ticket_number} for {user_phone}")
                
                state_manager.update_context(user_phone, {
                    "service_request_id": ticket_number,
                    "case_status": "SERVICE_REQUEST_CREATED"
                })
                
                state_manager.clear_state(user_phone)
                
                return (
                    "✅ Dhanyavaad.\n\n"
                    "Aapki service request safalta purvak create kar di gayi hai.\n\n"
                    f"📍 Location: {text_body.strip()}\n\n"
                    "Hamare service engineer jald hi aapse sampark karenge.\n\n"
                    "🙏 Thank You\n\n"
                    f"Service Request Status: Created\n"
                    f"Ticket Number: {ticket_number}"
                )
        except Exception as e:
            logger.error(f"Other: Service request creation failed: {str(e)}")
            state_manager.clear_state(user_phone)
            return (
                "⚠️ Service request create karne mein error aaya.\n\n"
                "Kripya support team se sampark karein."
            )
    
    # Handle alternate contact collection (when user doesn't know)
    if other_sub_step == "ALTERNATE_CONTACT":
        # Check if user still can't provide contact
        if _is_still_dont_know(text_body):
            logger.info(f"Other: User cannot provide alternate contact - manual review")
            
            state_manager.update_context(user_phone, {
                "case_status": "MANUAL_REVIEW_NO_INFORMATION",
                "reason": "USER_AND_NO_ALTERNATE_CONTACT"
            })
            
            state_manager.clear_state(user_phone)
            
            return (
                "Koi baat nahi. 🙏\n\n"
                "Humne aapki jankari note kar li hai.\n\n"
                "Humari team is case ko review karegi aur available information ke basis par action legi.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: Manual Review"
            )
        
        # Validate phone number
        if not _validate_phone(text_body):
            return (
                "⚠️ Kripya valid mobile number dein.\n\n"
                "Example: 9876543210 or +919876543210"
            )
        
        logger.info(f"Other: Alternate contact provided - creating manual review case")
        
        alternate_contact = text_body.strip()
        
        state_manager.update_context(user_phone, {
            "alternate_contact": alternate_contact,
            "case_status": "MANUAL_REVIEW_AWAITING_INFO",
            "case_type": "INFORMATION_PENDING"
        })
        
        state_manager.clear_state(user_phone)
        
        return (
            "✅ Dhanyavaad.\n\n"
            f"Humne alternate contact number note kar liya hai: {alternate_contact}\n\n"
            "Humari team unse sampark karegi vehicle ki sthiti ke baare mein jankari lene ke liye.\n\n"
            "🙏 Thank You\n\n"
            "Case Type: Information Pending\n"
            "Status: Awaiting Vehicle Information"
        )
    
    # Unknown step
    logger.warning(f"Unknown step in other issue flow: {current_step}")
    return "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein."
