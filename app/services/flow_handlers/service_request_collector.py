"""
Service Request Collector

Handles Q25-Q34: Collecting service request details before ticket creation.
This is shared across all flows that lead to "Service Request".
"""
import logging
import re
from datetime import datetime, date, time
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.ticket_service import create_service_request_ticket
from app.db.models.vehicle import Vehicle
from app.db.models.user import User

logger = logging.getLogger("app.service_request_collector")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """Check if response is affirmative"""
    return text in ["haan", "haa", "yes", "y", "h", "1", "हाँ", "हां"]


def _is_negative(text: str) -> bool:
    """Check if response is negative"""
    return text in ["nahi", "na", "no", "nahin", "n", "2", "नहीं"]


def _validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    cleaned = re.sub(r'[^\d+]', '', phone)
    return len(cleaned) >= 10 and len(cleaned) <= 15


def _validate_date(date_str: str) -> Optional[date]:
    """
    Validate and parse date in DD/MM/YYYY format.
    Returns date object if valid, None otherwise.
    """
    try:
        # Try DD/MM/YYYY
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        try:
            # Try DD-MM-YYYY
            return datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
        except ValueError:
            return None


def _validate_time(time_str: str) -> Optional[time]:
    """
    Validate and parse time in various formats.
    Returns time object if valid, None otherwise.
    """
    time_str = time_str.strip().lower()
    
    # Try HH:MM format (24-hour)
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        pass
    
    # Try H:MM format
    try:
        return datetime.strptime(time_str, "%I:%M").time()
    except ValueError:
        pass
    
    # Try with AM/PM
    for fmt in ["%I:%M %p", "%I:%M%p", "%I %p", "%I%p"]:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    return None


def _get_vehicle_info(user_phone: str, db: Session) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get vehicle number, owner name, owner mobile from database.
    Returns (vehicle_number, owner_name, owner_mobile)
    """
    try:
        user = db.query(User).filter(User.phone_number == user_phone).first()
        if not user:
            return None, None, None
        
        vehicle = db.query(Vehicle).filter(
            (Vehicle.manager_id == user.id) |
            (Vehicle.supervisor_id == user.id) |
            (Vehicle.driver_id == user.id)
        ).first()
        
        if not vehicle:
            return None, None, None
        
        # Get owner info (manager is usually the owner)
        if vehicle.manager_id:
            owner = db.query(User).filter(User.id == vehicle.manager_id).first()
            if owner:
                return vehicle.vehicle_number, owner.name, owner.phone_number
        
        return vehicle.vehicle_number, None, None
    except Exception as e:
        logger.error(f"Error getting vehicle info: {str(e)}")
        return None, None, None


def start_service_request_collection(
    user_phone: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Start collecting service request details (Q25-Q34).
    Pre-fill any known information from context or database.
    
    Args:
        user_phone: User's phone number
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        First question message
    """
    context = state_manager.get_context(user_phone)
    
    # Try to get vehicle info from database
    vehicle_number, owner_name, owner_mobile = _get_vehicle_info(user_phone, db)
    
    # Pre-fill known information
    if vehicle_number and not context.get("vehicle_number"):
        state_manager.update_context(user_phone, {"vehicle_number": vehicle_number})
    if owner_name and not context.get("owner_name"):
        state_manager.update_context(user_phone, {"owner_name": owner_name})
    if owner_mobile and not context.get("owner_mobile"):
        state_manager.update_context(user_phone, {"owner_mobile": owner_mobile})
    
    # Start with first missing field
    return _ask_next_field(user_phone, state_manager, db)


def _ask_next_field(
    user_phone: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Determine which field to ask next based on what's already collected.
    SMART COLLECTION: Skip fields that are already in context from the flow.
    """
    context = state_manager.get_context(user_phone)
    
    # Q25: Vehicle Number (skip if already in context)
    if not context.get("vehicle_number"):
        # Try one more time from database before asking
        vehicle_number_from_db, _, _ = _get_vehicle_info(user_phone, db)
        if vehicle_number_from_db:
            logger.info(f"Auto-filling vehicle number from database: {vehicle_number_from_db}")
            state_manager.update_context(user_phone, {"vehicle_number": vehicle_number_from_db})
            # Skip this question and move to next
            return _ask_next_field(user_phone, state_manager, db)
        
        # Really don't have it - ask user
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_VEHICLE_NUMBER)
        return (
            "📋 सर्विस रिक्वेस्ट के लिए कुछ जानकारी चाहिए।\n"
            "📋 We need some information for service request.\n\n"
            "🚗 वाहन नंबर क्या है?\n"
            "🚗 What is the vehicle number?\n\n"
            "उदाहरण / Example: MH12AB1234"
        )
    
    # Q26: Owner Name (skip if already in context)
    if not context.get("owner_name"):
        # Try one more time from database before asking
        _, owner_name_from_db, _ = _get_vehicle_info(user_phone, db)
        if owner_name_from_db:
            logger.info(f"Auto-filling owner name from database: {owner_name_from_db}")
            state_manager.update_context(user_phone, {"owner_name": owner_name_from_db})
            # Skip this question and move to next
            return _ask_next_field(user_phone, state_manager, db)
        
        # Really don't have it - ask user
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_OWNER_NAME)
        return (
            "👤 वाहन मालिक का नाम क्या है?\n"
            "👤 What is the vehicle owner's name?"
        )
    
    # Q27: Owner Mobile (skip if already in context - may come from Q7, Q11)
    if not context.get("owner_mobile"):
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_OWNER_MOBILE)
        return (
            "📞 मालिक का मोबाइल नंबर क्या है?\n"
            "📞 What is the owner's mobile number?\n\n"
            "उदाहरण / Example: +919876543210"
        )
    
    # Q28: Location (skip if already in context - may come from Q6, Q10, Q15, Q18)
    if not context.get("location"):
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_LOCATION)
        return (
            "📍 वाहन की वर्तमान लोकेशन क्या है?\n"
            "📍 What is the vehicle's current location?\n\n"
            "कृपया पूरा पता दें।\n"
            "Please provide full address."
        )
    
    # Q29: Driver Name (skip if already in context - may come from Q13)
    if not context.get("driver_name"):
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_DRIVER_NAME)
        return (
            "👨‍✈️ ड्राइवर का नाम क्या है?\n"
            "👨‍✈️ What is the driver's name?\n\n"
            "(अगर कोई ड्राइवर नहीं है तो 'NA' टाइप करें)\n"
            "(Type 'NA' if no driver)"
        )
    
    # Q30: Driver Mobile (skip if already in context - may come from Q14)
    if not context.get("driver_mobile"):
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_DRIVER_MOBILE)
        return (
            "📞 ड्राइवर का मोबाइल नंबर क्या है?\n"
            "📞 What is the driver's mobile number?\n\n"
            "(अगर नहीं है तो 'NA' टाइप करें)\n"
            "(Type 'NA' if not available)"
        )
    
    # Q31: Vehicle Available? (skip if already in context - may come from Q8)
    if context.get("vehicle_available") is None:
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_VEHICLE_AVAILABLE)
        return (
            "🚗 क्या वाहन inspection के लिए उपलब्ध है?\n"
            "🚗 Is vehicle available for inspection?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )
    
    # Q32: Visit Date (skip if already in context - may come from Q5, Q9, Q12, Q16, Q19)
    # Check multiple possible fields: inspection_date, reinstallation_date, vehicle_available_date
    if not context.get("visit_date") and not context.get("inspection_date") and not context.get("reinstallation_date"):
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_VISIT_DATE)
        return (
            "📅 किस तारीख को visit करें?\n"
            "📅 Preferred visit date?\n\n"
            "कृपया DD/MM/YYYY फॉर्मेट में दें।\n"
            "Please provide in DD/MM/YYYY format.\n\n"
            "उदाहरण / Example: 15/06/2026"
        )
    else:
        # Use already collected date/time
        if context.get("inspection_date"):
            context["visit_date"] = context.get("inspection_date")
            context["visit_time"] = context.get("inspection_time", "")
        elif context.get("reinstallation_date"):
            context["visit_date"] = context.get("reinstallation_date")
            context["visit_time"] = context.get("reinstallation_time", "")
        elif context.get("vehicle_available_date"):
            context["visit_date"] = context.get("vehicle_available_date")
            context["visit_time"] = context.get("vehicle_available_time", "")
        state_manager.update_context(user_phone, context)
    
    # Q33: Visit Time (skip if already in context with date)
    if not context.get("visit_time") and not context.get("inspection_time") and not context.get("reinstallation_time"):
        state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_VISIT_TIME)
        return (
            "🕐 किस समय visit करें?\n"
            "🕐 Preferred visit time?\n\n"
            "उदाहरण / Examples:\n"
            "• 10:00 AM\n"
            "• 14:30\n"
            "• 2:00 PM"
        )
    
    # Q34: Issue Type (infer from issue_classification if available)
    if not context.get("issue_type_detail"):
        # Try to map from issue_classification
        issue_classification = context.get("issue_classification", "")
        issue_type_map = {
            "GPS_REMOVED": "GPS Removed",
            "GPS_DAMAGED": "GPS Damaged",
            "VEHICLE_RUNNING": "GPS Not Working",
            "VEHICLE_STANDING": "GPS Not Working",
            "BATTERY_DISCONNECT": "Battery Related",
            "WORKSHOP": "Other",
            "ACCIDENT": "Accident Related"
        }
        
        inferred_type = issue_type_map.get(issue_classification)
        if inferred_type:
            # Auto-fill based on classification
            state_manager.update_context(user_phone, {"issue_type_detail": inferred_type})
        else:
            # Ask user to select
            state_manager.set_state(user_phone, ConversationStep.DATA_COLLECTION_ISSUE_TYPE)
            return (
                "🔧 Issue का type क्या है?\n"
                "🔧 What is the issue type?\n\n"
                "1️⃣ GPS Not Working\n"
                "2️⃣ GPS Removed\n"
                "3️⃣ GPS Damaged\n"
                "4️⃣ Battery Related\n"
                "5️⃣ GPS Reinstallation\n"
                "6️⃣ Accident Related\n"
                "7️⃣ Other\n\n"
                "कृपया नंबर चुनें / Please select number"
            )
    
    # All fields collected - proceed to Q35 (engineer assignment)
    return _proceed_to_engineer_assignment(user_phone, state_manager, db)


def handle_service_request_response(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle user responses during service request data collection.
    
    Args:
        user_phone: User's phone number
        text_body: User's response
        current_step: Current conversation step
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        Next question or confirmation message
    """
    normalized = _normalize_text(text_body)
    context = state_manager.get_context(user_phone)
    
    # Q25: Vehicle Number
    if current_step == ConversationStep.DATA_COLLECTION_VEHICLE_NUMBER.value:
        # Check for conversational responses that indicate user expects we already have it
        conversational_indicators = [
            "tumhare pass", "aapke pass", "already", "pehle se", "vo toh",
            "you have", "you already", "मेरे पास नहीं", "पता नहीं", "don't know"
        ]
        
        is_conversational = any(indicator in normalized for indicator in conversational_indicators)
        
        if is_conversational:
            # Try to get vehicle number from database or initial context
            vehicle_number = context.get("vehicle_number")
            
            if not vehicle_number:
                # Try from database
                vehicle_number, _, _ = _get_vehicle_info(user_phone, db)
            
            if vehicle_number:
                logger.info(f"Using pre-filled vehicle number: {vehicle_number}")
                state_manager.update_context(user_phone, {"vehicle_number": vehicle_number})
                return _ask_next_field(user_phone, state_manager, db)
            else:
                # Still don't have it - ask again more clearly
                return (
                    "🚗 कृपया वाहन नंबर बताएं।\n"
                    "🚗 Please provide the vehicle number.\n\n"
                    "उदाहरण / Example: MH12AB1234"
                )
        
        # Normal vehicle number validation
        vehicle_number = text_body.strip().upper().replace(" ", "")
        if len(vehicle_number) < 6 or not re.match(r'^[A-Z0-9]+$', vehicle_number):
            return (
                "⚠️ कृपया सही vehicle number दें।\n"
                "⚠️ Please provide valid vehicle number.\n\n"
                "उदाहरण / Example: MH12AB1234"
            )
        
        state_manager.update_context(user_phone, {"vehicle_number": vehicle_number})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q26: Owner Name
    elif current_step == ConversationStep.DATA_COLLECTION_OWNER_NAME.value:
        if len(text_body.strip()) < 2:
            return (
                "⚠️ कृपया मालिक का नाम दें।\n"
                "⚠️ Please provide owner's name."
            )
        
        state_manager.update_context(user_phone, {"owner_name": text_body.strip()})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q27: Owner Mobile
    elif current_step == ConversationStep.DATA_COLLECTION_OWNER_MOBILE.value:
        if not _validate_phone(text_body):
            return (
                "⚠️ कृपया सही mobile number दें।\n"
                "⚠️ Please provide valid mobile number.\n\n"
                "उदाहरण / Example: +919876543210 या 9876543210"
            )
        
        state_manager.update_context(user_phone, {"owner_mobile": text_body.strip()})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q28: Location
    elif current_step == ConversationStep.DATA_COLLECTION_LOCATION.value:
        if len(text_body.strip()) < 5:
            return (
                "⚠️ कृपया पूरा पता दें।\n"
                "⚠️ Please provide complete address."
            )
        
        state_manager.update_context(user_phone, {"location": text_body.strip()})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q29: Driver Name
    elif current_step == ConversationStep.DATA_COLLECTION_DRIVER_NAME.value:
        driver_name = text_body.strip() if normalized != "na" else "Not Available"
        state_manager.update_context(user_phone, {"driver_name": driver_name})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q30: Driver Mobile
    elif current_step == ConversationStep.DATA_COLLECTION_DRIVER_MOBILE.value:
        if normalized == "na":
            driver_mobile = "Not Available"
        elif _validate_phone(text_body):
            driver_mobile = text_body.strip()
        else:
            return (
                "⚠️ कृपया सही mobile number दें या 'NA' टाइप करें।\n"
                "⚠️ Please provide valid mobile number or type 'NA'."
            )
        
        state_manager.update_context(user_phone, {"driver_mobile": driver_mobile})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q31: Vehicle Available?
    elif current_step == ConversationStep.DATA_COLLECTION_VEHICLE_AVAILABLE.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user_phone, {"vehicle_available": True})
        elif _is_negative(normalized):
            state_manager.update_context(user_phone, {"vehicle_available": False})
        else:
            return (
                "⚠️ कृपया 1 (हाँ) या 2 (नहीं) चुनें।\n"
                "⚠️ Please select 1 (Yes) or 2 (No)."
            )
        
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q32: Visit Date
    elif current_step == ConversationStep.DATA_COLLECTION_VISIT_DATE.value:
        parsed_date = _validate_date(text_body)
        if not parsed_date:
            return (
                "⚠️ कृपया सही date format दें।\n"
                "⚠️ Please provide valid date format.\n\n"
                "Format: DD/MM/YYYY\n"
                "उदाहरण / Example: 15/06/2026"
            )
        
        # Check if date is not in the past
        if parsed_date < date.today():
            return (
                "⚠️ पुरानी तारीख नहीं चुन सकते।\n"
                "⚠️ Cannot select past date.\n\n"
                "कृपया आज या भविष्य की तारीख दें।\n"
                "Please provide today or future date."
            )
        
        state_manager.update_context(user_phone, {"visit_date": parsed_date.isoformat()})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q33: Visit Time
    elif current_step == ConversationStep.DATA_COLLECTION_VISIT_TIME.value:
        parsed_time = _validate_time(text_body)
        if not parsed_time:
            return (
                "⚠️ कृपया सही time format दें।\n"
                "⚠️ Please provide valid time format.\n\n"
                "उदाहरण / Examples:\n"
                "• 10:00 AM\n"
                "• 14:30\n"
                "• 2 PM"
            )
        
        state_manager.update_context(user_phone, {"visit_time": parsed_time.isoformat()})
        return _ask_next_field(user_phone, state_manager, db)
    
    # Q34: Issue Type
    elif current_step == ConversationStep.DATA_COLLECTION_ISSUE_TYPE.value:
        issue_type_map = {
            "1": "GPS Not Working",
            "2": "GPS Removed",
            "3": "GPS Damaged",
            "4": "Battery Related",
            "5": "GPS Reinstallation",
            "6": "Accident Related",
            "7": "Other"
        }
        
        issue_type = issue_type_map.get(normalized)
        if not issue_type:
            return (
                "⚠️ कृपया 1-7 के बीच नंबर चुनें।\n"
                "⚠️ Please select number between 1-7."
            )
        
        state_manager.update_context(user_phone, {"issue_type_detail": issue_type})
        return _proceed_to_engineer_assignment(user_phone, state_manager, db)
    
    return "⚠️ कुछ गलत हो गया। / Something went wrong."


def _proceed_to_engineer_assignment(
    user_phone: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    All data collected - show summary and ask Q35 (engineer assignment).
    """
    context = state_manager.get_context(user_phone)
    
    # Format date and time for display
    visit_date_str = context.get("visit_date", "Not specified")
    if visit_date_str and visit_date_str != "Not specified":
        try:
            visit_date_obj = datetime.fromisoformat(visit_date_str).date()
            visit_date_str = visit_date_obj.strftime("%d/%m/%Y")
        except:
            pass
    
    visit_time_str = context.get("visit_time", "Not specified")
    if visit_time_str and visit_time_str != "Not specified":
        try:
            visit_time_obj = datetime.fromisoformat(visit_time_str).time()
            visit_time_str = visit_time_obj.strftime("%I:%M %p")
        except:
            pass
    
    # Show summary
    summary = (
        "✅ जानकारी मिल गई! / Information received!\n\n"
        "📋 **सर्विस रिक्वेस्ट सारांश / Service Request Summary:**\n\n"
        f"🚗 Vehicle: {context.get('vehicle_number', 'N/A')}\n"
        f"👤 Owner: {context.get('owner_name', 'N/A')}\n"
        f"📞 Owner Mobile: {context.get('owner_mobile', 'N/A')}\n"
        f"📍 Location: {context.get('location', 'N/A')}\n"
        f"👨‍✈️ Driver: {context.get('driver_name', 'N/A')}\n"
        f"📞 Driver Mobile: {context.get('driver_mobile', 'N/A')}\n"
        f"📅 Visit Date: {visit_date_str}\n"
        f"🕐 Visit Time: {visit_time_str}\n"
        f"🔧 Issue: {context.get('issue_type_detail', context.get('issue_classification', 'N/A'))}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "क्या हम नज़दीकी सर्विस इंजीनियर को असाइन करें?\n"
        "Should we assign the nearest service engineer?\n\n"
        "1️⃣ हाँ / Yes\n"
        "2️⃣ नहीं / No"
    )
    
    state_manager.set_state(user_phone, ConversationStep.ENGINEER_ASSIGNMENT)
    return summary
