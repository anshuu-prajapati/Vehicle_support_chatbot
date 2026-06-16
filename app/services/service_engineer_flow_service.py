"""
Service Engineer Flow Service

Main handler for the service engineer assignment workflow.
Routes incoming messages to appropriate flow handlers based on issue classification.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.intent_classification_service import classify_customer_intent, get_issue_type_display_name
from app.services.greeting_service import GreetingService
from app.services.vehicle_status_service import VehicleStatusService
from app.services.ticket_service import create_service_request_ticket, assign_engineer, update_ticket
from app.db.models.vehicle import Vehicle
from app.db.models.user import User

# Import all flow handlers
from app.services.flow_handlers.workshop_flow import handle_workshop_flow
from app.services.flow_handlers.accident_flow import handle_accident_flow
from app.services.flow_handlers.battery_flow import handle_battery_flow
from app.services.flow_handlers.gps_removed_flow import handle_gps_removed_flow
from app.services.flow_handlers.gps_damaged_flow import handle_gps_damaged_flow
from app.services.flow_handlers.vehicle_standing_flow import handle_vehicle_standing_flow
from app.services.flow_handlers.vehicle_running_flow import handle_vehicle_running_flow
from app.services.flow_handlers.other_issue_flow import handle_other_issue_flow
from app.services.flow_handlers.service_request_collector import (
    handle_service_request_response
)

logger = logging.getLogger("app.service_engineer_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """Check if response is affirmative"""
    return text in ["haan", "haa", "yes", "y", "h", "1"]


def _is_negative(text: str) -> bool:
    """Check if response is negative"""
    return text in ["nahi", "na", "no", "nahin", "n", "2"]


def _get_vehicle_number_for_user(user_phone: str, db: Session) -> Optional[str]:
    """Get vehicle number associated with a user"""
    try:
        user = db.query(User).filter(User.phone_number == user_phone).first()
        if not user:
            return None
        
        vehicle = db.query(Vehicle).filter(
            (Vehicle.manager_id == user.id) |
            (Vehicle.supervisor_id == user.id) |
            (Vehicle.driver_id == user.id)
        ).first()
        
        return vehicle.vehicle_number if vehicle else None
    except Exception as e:
        logger.error(f"Error getting vehicle number: {str(e)}")
        return None


def check_vehicle_inactive_duration(
    vehicle_number: str,
    db: Session
) -> Tuple[bool, float, str, str]:
    """
    Check if vehicle has been inactive for more than 48 hours.
    
    Args:
        vehicle_number: Vehicle registration number
        db: Database session
        
    Returns:
        Tuple of (should_auto_close, hours_inactive, last_location, last_time)
    """
    try:
        status_service = VehicleStatusService(db)
        vehicle_status = status_service.get_vehicle_status(vehicle_number)
        
        if not vehicle_status:
            logger.warning(f"No status found for vehicle {vehicle_number}")
            return False, 0.0, "Unknown", "Unknown"
        
        last_gps_time = vehicle_status.get("last_gps_time")
        location = vehicle_status.get("location", "Unknown location")
        
        if not last_gps_time:
            logger.warning(f"No GPS time for vehicle {vehicle_number}")
            return False, 0.0, location, "Unknown"
        
        # Parse last GPS time
        if isinstance(last_gps_time, str):
            last_gps_dt = datetime.fromisoformat(last_gps_time.replace('Z', '+00:00'))
        else:
            last_gps_dt = last_gps_time
        
        # Calculate hours inactive
        now = datetime.now(last_gps_dt.tzinfo) if last_gps_dt.tzinfo else datetime.now()
        hours_inactive = (now - last_gps_dt).total_seconds() / 3600
        
        # Should auto-close if > 48 hours
        should_close = hours_inactive > 48
        
        logger.info(
            f"Inactive duration check for {vehicle_number}: {hours_inactive:.1f} hours",
            extra={
                "vehicle_number": vehicle_number,
                "hours_inactive": hours_inactive,
                "should_auto_close": should_close
            }
        )
        
        return should_close, hours_inactive, location, last_gps_dt.strftime('%d/%m/%Y %H:%M')
        
    except Exception as e:
        logger.error(f"Error checking inactive duration: {str(e)}", exc_info=True)
        return False, 0.0, "Unknown", "Unknown"


def _route_to_flow_handler(
    user_phone: str,
    issue_type: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Route to appropriate flow handler based on issue type.
    User has already selected option 1-8, route directly to flow start.
    
    Args:
        user_phone: User's phone number
        issue_type: Classified issue type
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        First question for the specific flow
    """
    
    if issue_type == "WORKSHOP":
        state_manager.set_state(user_phone, ConversationStep.WORKSHOP_CONFIRMATION)
        return (
            "Kya vehicle filhaal workshop/service center mein repair ya maintenance ke liye hai?\n\n"
            "1️⃣ Yes\n"
            "2️⃣ No"
        )
    
    elif issue_type == "ACCIDENT":
        state_manager.set_state(user_phone, ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION)
        state_manager.update_context(user_phone, {"accident_sub_step": "ACCIDENT_EXPECTED_DATE"})
        return (
            "Dhanyavaad. 🙏\n\n"
            "Kripya vehicle ke dobara chalu hone ya workshop se bahar aane ki expected date batayein.\n\n"
            "📅 Expected Date: (Example: 20-06-2026)"
        )
    
    elif issue_type == "BATTERY_DISCONNECT":
        state_manager.set_state(user_phone, ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION)
        return (
            "Kya vehicle ki battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?\n\n"
            "1️⃣ Yes\n"
            "2️⃣ No"
        )
    
    elif issue_type == "GPS_REMOVED":
        state_manager.set_state(user_phone, ConversationStep.GPS_REMOVED_REINSTALL_DATE)
        return (
            "Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?\n\n"
            "1️⃣ Yes\n"
            "2️⃣ No"
        )
    
    elif issue_type == "GPS_DAMAGED":
        state_manager.set_state(user_phone, ConversationStep.GPS_DAMAGED_LOCATION)
        return (
            "Vehicle ki current location kya hai?\n"
            "What is the current vehicle location?\n\n"
            "Kripya pura address dein.\n"
            "Please provide full address."
        )
    
    elif issue_type == "VEHICLE_RUNNING":
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_RUNNING_DRIVER_NAME)
        return (
            "Driver ka naam kya hai?\n"
            "What is the driver's name?"
        )
    
    elif issue_type == "VEHICLE_STANDING":
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_STANDING_DURATION)
        return (
            "Vehicle kitne samay se khadi hai?\n"
            "For how long has the vehicle been standing?\n\n"
            "1️⃣ 24 ghante se kam / Less than 24 hrs\n"
            "2️⃣ 24-48 ghante / 24-48 hrs\n"
            "3️⃣ 48 ghante se adhik / More than 48 hrs"
        )
    
    else:  # UNKNOWN or OTHER
        state_manager.set_state(user_phone, ConversationStep.OTHER_ISSUE_DESCRIPTION)
        return (
            "Kripya issue thoda aur detail mein batayein.\n"
            "Please explain the issue in more detail.\n\n"
            "Yeh humein sahi tarike se madad karne mein sahayata karega.\n"
            "This will help us assist you correctly."
        )


def handle_engineer_assignment(
    user_phone: str,
    text_body: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle engineer assignment confirmation (Q35).
    
    Args:
        user_phone: User's phone number
        text_body: User's response
        state_manager: StateManager instance
        db: Session: Database session
        
    Returns:
        Response message
    """
    normalized = _normalize_text(text_body)
    context = state_manager.get_context(user_phone)
    ticket_number = context.get("service_request_id")
    
    if not ticket_number:
        logger.error(f"Engineer assignment: No ticket found", extra={"phone": user_phone})
        state_manager.clear_state(user_phone)
        return "⚠️ टिकट नहीं मिला। / Ticket not found."
    
    if _is_affirmative(normalized):
        # Assign nearest engineer (placeholder - implement actual logic)
        # For now, just update status to ASSIGNED
        try:
            update_ticket(ticket_number, status="ASSIGNED")
            
            logger.info(
                f"Engineer assignment: Ticket assigned",
                extra={"phone": user_phone, "ticket": ticket_number}
            )
            
            # Clear conversation state
            state_manager.clear_state(user_phone)
            
            return (
                "✅ सर्विस इंजीनियर असाइन कर दिया गया है!\n"
                "✅ Service engineer has been assigned!\n\n"
                f"🎫 टिकट नंबर / Ticket Number: {ticket_number}\n\n"
                "इंजीनियर जल्द ही आपसे संपर्क करेगा।\n"
                "Engineer will contact you soon.\n\n"
                "📞 आप इंजीनियर से जुड़ेंगे जैसे ही वह उपलब्ध होगा।\n"
                "📞 You will be connected with engineer as soon as available.\n\n"
                "धन्यवाद! / Thank you!"
            )
        except Exception as e:
            logger.error(f"Engineer assignment failed: {str(e)}", exc_info=True)
            state_manager.clear_state(user_phone)
            return (
                "⚠️ असाइनमेंट में त्रुटि हुई।\n"
                "⚠️ Error in assignment.\n\n"
                "कृपया सपोर्ट टीम से संपर्क करें।\n"
                "Please contact support team."
            )
    
    elif _is_negative(normalized):
        # Keep on hold
        try:
            update_ticket(ticket_number, status="ON_HOLD")
            
            logger.info(
                f"Engineer assignment: Kept on hold",
                extra={"phone": user_phone, "ticket": ticket_number}
            )
            
            # Clear conversation state
            state_manager.clear_state(user_phone)
            
            return (
                "✅ ठीक है। टिकट ऑन होल्ड रखा गया है।\n"
                "✅ Okay. Ticket has been kept on hold.\n\n"
                f"🎫 टिकट नंबर / Ticket Number: {ticket_number}\n\n"
                "जब आप तैयार हों, तो हमें बताएं।\n"
                "When you're ready, let us know.\n\n"
                "धन्यवाद! / Thank you!"
            )
        except Exception as e:
            logger.error(f"Hold status update failed: {str(e)}", exc_info=True)
            state_manager.clear_state(user_phone)
            return "⚠️ त्रुटि हुई। / Error occurred."
    
    else:
        # Invalid response
        return (
            "⚠️ कृपया वैध विकल्प चुनें।\n"
            "⚠️ Please select a valid option.\n\n"
            "क्या हम नज़दीकी सर्विस इंजीनियर को असाइन करें?\n"
            "Should we assign the nearest service engineer?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )


def handle_service_engineer_message(
    user,
    text_body: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Main entry point for service engineer assignment workflow.
    
    Args:
        user: User object with phone_number
        text_body: Message text from user
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        Response message to send to user
    """
    try:
        # Check for reset command first
        from app.services.fallback_handler import should_reset_conversation
        if should_reset_conversation(text_body):
            logger.info(f"User {user.phone_number} requested conversation reset")
            state_manager.clear_state(user.phone_number)
            return (
                "✅ बातचीत रीसेट हो गई है।\n"
                "✅ Conversation has been reset.\n\n"
                "आप नए सिरे से शुरू कर सकते हैं।\n"
                "You can start fresh.\n\n"
                "कृपया अपना सवाल या समस्या बताएं।\n"
                "Please tell us your question or issue."
            )
        
        return _handle_service_engineer_message_internal(user, text_body, state_manager, db)
    
    except Exception as e:
        logger.error(
            f"CRITICAL ERROR in service engineer flow for {user.phone_number}: {str(e)}",
            exc_info=True,
            extra={
                "phone": user.phone_number,
                "user_message": text_body[:100],
                "error_type": type(e).__name__
            }
        )
        
        # Never break - always return helpful message
        # Clear state to allow fresh start
        try:
            state_manager.clear_state(user.phone_number)
        except:
            pass
        
        return (
            "⚠️ माफ़ कीजिये, कुछ technical समस्या आ गई।\n"
            "⚠️ Sorry, a technical issue occurred.\n\n"
            "बातचीत रीसेट कर दी गई है।\n"
            "Conversation has been reset.\n\n"
            "कृपया फिर से शुरू करें या 'reset' टाइप करें।\n"
            "Please start again or type 'reset'.\n\n"
            "अगर समस्या बनी रहे, तो सपोर्ट टीम से संपर्क करें।\n"
            "If problem persists, contact support team."
        )


def _handle_service_engineer_message_internal(
    user,
    text_body: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Internal handler with error handling wrapper.
    """
    normalized = _normalize_text(text_body)
    greeting_service = GreetingService(state_manager)
    
    # Get current state
    state = state_manager.get_state(user.phone_number)
    
    # Handle initial status selection (numeric OR natural language)
    # This applies when user has NO active conversation (or is at MAIN_MENU)
    if not state or state.current_step == ConversationStep.MAIN_MENU.value:
        # Check if it's a numeric selection (1-8)
        if normalized in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            logger.info(f"User {user.phone_number} selected option {normalized} from GPS alert")
            
            # Map number to issue type
            numeric_map = {
                "1": "WORKSHOP",
                "2": "ACCIDENT",
                "3": "BATTERY_DISCONNECT",
                "4": "GPS_REMOVED",
                "5": "GPS_DAMAGED",
                "6": "VEHICLE_RUNNING",
                "7": "VEHICLE_STANDING",
                "8": "UNKNOWN"
            }
            
            issue_type = numeric_map[normalized]
            
            # Store in context
            state_manager.update_context(user.phone_number, {
                "issue_classification": issue_type,
                "classification_method": "NUMERIC_DIRECT",
                "customer_response": text_body
            })
            
            # Route directly to flow
            return _route_to_flow_handler(user.phone_number, issue_type, state_manager, db)
        
        # Not a number - check if it's a natural language response
        # Skip if it's a greeting (will be handled below)
        if not greeting_service.is_greeting(normalized):
            # Try to classify the user's natural language input
            logger.info(f"User {user.phone_number} sent natural language: '{text_body[:50]}...'")
            
            issue_type, method = classify_customer_intent(text_body)
            
            logger.info(
                f"Initial selection classified as: {issue_type} using {method}",
                extra={
                    "phone": user.phone_number,
                    "message": text_body[:100],
                    "classification": issue_type,
                    "method": method
                }
            )
            
            # If classification is confident (not UNKNOWN), route automatically
            if issue_type != "UNKNOWN":
                # Store in context
                state_manager.update_context(user.phone_number, {
                    "issue_classification": issue_type,
                    "classification_method": f"NLP_{method}",
                    "customer_response": text_body
                })
                
                # Route directly to flow
                return _route_to_flow_handler(user.phone_number, issue_type, state_manager, db)
            
            # Classification returned UNKNOWN - ask user to select from options
            logger.info(f"Could not classify '{text_body[:50]}' - asking for selection")
            return (
                "⚠️ Kripya option number select karein.\n\n"
                "1️⃣ Workshop / Service Center\n"
                "2️⃣ Accident\n"
                "3️⃣ Battery Disconnect\n"
                "4️⃣ GPS Removed\n"
                "5️⃣ GPS Damaged\n"
                "6️⃣ Vehicle Running but GPS Not Updating\n"
                "7️⃣ Vehicle Standing\n"
                "8️⃣ Other"
            )
    
    # Handle greetings
    if greeting_service.is_greeting(normalized):
        logger.info(f"Greeting detected from {user.phone_number}")
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)
    
    # Check if we have an active state
    if not state:
        # No state - send welcome
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)
    
    current_step = state.current_step
    
    # Handle engineer assignment step
    if current_step == ConversationStep.ENGINEER_ASSIGNMENT.value:
        return handle_engineer_assignment(user.phone_number, text_body, state_manager, db)
    
    # Handle service request data collection steps (Q25-Q34)
    if current_step in [
        ConversationStep.DATA_COLLECTION_VEHICLE_NUMBER.value,
        ConversationStep.DATA_COLLECTION_OWNER_NAME.value,
        ConversationStep.DATA_COLLECTION_OWNER_MOBILE.value,
        ConversationStep.DATA_COLLECTION_DRIVER_NAME.value,
        ConversationStep.DATA_COLLECTION_DRIVER_MOBILE.value,
        ConversationStep.DATA_COLLECTION_LOCATION.value,
        ConversationStep.DATA_COLLECTION_VEHICLE_AVAILABLE.value,
        ConversationStep.DATA_COLLECTION_VISIT_DATE.value,
        ConversationStep.DATA_COLLECTION_VISIT_TIME.value,
        ConversationStep.DATA_COLLECTION_ISSUE_TYPE.value,
    ]:
        return handle_service_request_response(
            user.phone_number, text_body, current_step, state_manager, db
        )
    
    # Route to specific flow handlers based on current step
    try:
        # Workshop Flow
        if current_step == ConversationStep.WORKSHOP_CONFIRMATION.value:
            return handle_workshop_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # Accident Flow
        elif current_step == ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION.value:
            return handle_accident_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # Battery Flow
        elif current_step in [
            ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION.value,
            ConversationStep.BATTERY_GPS_REINSTALL_CONFIRMATION.value,
            ConversationStep.BATTERY_GPS_DATA_CHECK.value,
        ]:
            return handle_battery_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # GPS Removed Flow (Q5-Q9)
        elif current_step in [
            ConversationStep.GPS_REMOVED_REINSTALL_DATE.value,     # Q5
            ConversationStep.GPS_REMOVED_LOCATION.value,           # Q6
            ConversationStep.GPS_REMOVED_CONTACT.value,            # Q7
            ConversationStep.GPS_REMOVED_AVAILABILITY.value,       # Q8
            ConversationStep.GPS_REMOVED_AVAILABLE_DATE.value,     # Q9
        ]:
            return handle_gps_removed_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # GPS Damaged Flow (Q10-Q12)
        elif current_step in [
            ConversationStep.GPS_DAMAGED_LOCATION.value,           # Q10
            ConversationStep.GPS_DAMAGED_CONTACT.value,            # Q11
            ConversationStep.GPS_DAMAGED_INSPECTION_DATE.value,    # Q12
        ]:
            return handle_gps_damaged_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # Vehicle Running Flow (Q13-Q16)
        elif current_step in [
            ConversationStep.VEHICLE_RUNNING_DRIVER_NAME.value,       # Q13
            ConversationStep.VEHICLE_RUNNING_DRIVER_MOBILE.value,     # Q14
            ConversationStep.VEHICLE_RUNNING_LOCATION.value,          # Q15
            ConversationStep.VEHICLE_RUNNING_INSPECTION_DATE.value,   # Q16
        ]:
            return handle_vehicle_running_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # Vehicle Standing Flow (Q17-Q19)
        elif current_step in [
            ConversationStep.VEHICLE_STANDING_DURATION.value,         # Q17
            ConversationStep.VEHICLE_STANDING_LOCATION.value,         # Q18
            ConversationStep.VEHICLE_STANDING_INSPECTION_DATE.value,  # Q19
        ]:
            return handle_vehicle_standing_flow(user.phone_number, text_body, current_step, state_manager, db)
        
        # Other/Unknown Issue Flow (Q20)
        elif current_step in [
            ConversationStep.OTHER_ISSUE_DESCRIPTION.value,     # Q20
        ]:
            return handle_other_issue_flow(user.phone_number, text_body, current_step, state_manager, db)
    
    except Exception as flow_error:
        logger.error(
            f"Flow handler error at step {current_step}: {str(flow_error)}",
            exc_info=True,
            extra={"phone": user.phone_number, "step": current_step}
        )
        
        # Don't break - ask user to retry or reset
        return (
            "⚠️ कुछ गलत हो गया।\n"
            "⚠️ Something went wrong.\n\n"
            "कृपया अपना जवाब फिर से भेजें या 'reset' टाइप करें।\n"
            "Please send your response again or type 'reset'."
        )
    
    # Unknown state - reset
    logger.warning(f"Unknown state: {current_step} for user {user.phone_number}")
    state_manager.clear_state(user.phone_number)
    return (
        "⚠️ कुछ गलत हो गया। बातचीत रीसेट हो गई है।\n"
        "⚠️ Something went wrong. Conversation has been reset.\n\n"
        "कृपया फिर से शुरू करें।\n"
        "Please start again."
    )
