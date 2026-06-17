"""
GPS Removed Flow Handler

Flow:
Customer selects: 4️⃣ GPS Removed
Q1: Maintenance/Repair confirmation (LLM-driven)
  - YES → Q2: Expected date → Close Case  
  - NO → GPS Reinstallation Flow (Q3-Q7) → Service Request
"""
import logging
import re
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.ticket_service import create_service_request_ticket
from app.services.clarification_handler import (
    should_clarify,
    generate_clarification_response,
    get_context_explanation_for_step,
    get_current_question_text
)

logger = logging.getLogger("app.gps_removed_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _validate_date(date_str: str) -> tuple:
    """
    Validate and parse date in DD-MM-YYYY or DD/MM/YYYY format.
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
            return None, "Invalid date format. Please use DD-MM-YYYY or DD/MM/YYYY (Example: 20-06-2026)"


def _validate_phone(phone: str) -> bool:
    """Validate phone number"""
    cleaned = re.sub(r'[^\d+]', '', phone)
    return len(cleaned) >= 10 and len(cleaned) <= 15


def _is_temporary_removal(text: str) -> bool:
    """
    Check if GPS removal is temporary (maintenance/repair) using LLM understanding.
    Returns True if temporary removal for maintenance/repair/testing.
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
        prompt = f"""Determine if GPS device was removed temporarily for maintenance/repair/testing.

User was asked: "Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?"

User replied: "{text}"

Examples of YES (temporary removal for maintenance):
- "haan maintenance ke liye nikala hai"
- "service ke liye remove kiya hai"
- "repair chal rahi hai"
- "testing ke liye nikala hai"
- "checking ke liye remove kiya"

Examples of NO (permanent removal or reinstallation needed):
- "nahi"
- "GPS nikal gaya hai"
- "GPS dobara lagwana hai"
- "GPS reinstall karna hai"
- "device remove ho gaya hai"
- "chori ho gaya"

Respond with ONLY ONE WORD: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM temporary removal check: '{text[:50]}' -> {response}")
        
        return response == "YES"
        
    except Exception as e:
        logger.error(f"LLM temporary removal check failed: {str(e)}")
        # Fallback to keyword matching
        temp_keywords = ["maintenance", "repair", "service", "testing", "checking"]
        permanent_keywords = ["dobara", "reinstall", "lagwana", "chori", "stolen"]
        
        has_temp = any(keyword in normalized for keyword in temp_keywords)
        has_permanent = any(keyword in normalized for keyword in permanent_keywords)
        
        if has_permanent:
            return False
        return has_temp


def _wants_alternate_number(text: str) -> bool:
    """
    Check if user wants to use alternate contact number using LLM understanding.
    Returns True if wants alternate number.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for affirmative (same number)
    same_number_patterns = ["isi number", "same number", "yehi number", "this number", "haan"]
    if any(pattern in normalized for pattern in same_number_patterns):
        return False
    
    # Quick check for alternate number request
    alternate_patterns = ["alternate", "dusra", "doosra", "different", "aur number"]
    if any(pattern in normalized for pattern in alternate_patterns):
        return True
    
    # Use LLM for natural language understanding
    try:
        prompt = f"""Determine if user wants to use an alternate contact number or the same registered number.

User was asked: "Kya engineer isi number par sampark kare ya koi aur number use kare?"

User replied: "{text}"

Examples of SAME NUMBER (no alternate):
- "isi number par sampark karein"
- "same number"
- "yehi number theek hai"
- "haan isi par"

Examples of ALTERNATE NUMBER:
- "is number par nahi"
- "alternate number use karein"
- "doosra number note karein"
- "different number"

Respond with: SAME or ALTERNATE"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM contact number check: '{text[:50]}' -> {response}")
        
        return response == "ALTERNATE"
        
    except Exception as e:
        logger.error(f"LLM contact number check failed: {str(e)}")
        # Fallback
        return any(word in normalized for word in ["alternate", "dusra", "doosra", "aur number"])


def _has_additional_info(text: str) -> bool:
    """
    Check if user wants to provide additional information using LLM understanding.
    Returns True if wants to provide info.
    """
    normalized = text.strip().lower() if text else ""
    
    # Quick check
    if normalized in ["nahi", "na", "no"]:
        return False
    
    # If user provides actual information (more than just yes/no)
    if len(text.strip()) > 10:
        return True
    
    return False


def _get_registered_mobile(user_phone: str, db: Session) -> str:
    """Get registered mobile number for user"""
    try:
        from app.db.models.user import User
        user = db.query(User).filter(User.phone_number == user_phone).first()
        return user.phone_number if user else user_phone
    except Exception as e:
        logger.error(f"Error getting registered mobile: {str(e)}")
        return user_phone


def _get_vehicle_number_from_db(user_phone: str, db: Session) -> str:
    """Get vehicle number associated with user from database"""
    try:
        from app.db.models.user import User
        from app.db.models.vehicle import Vehicle
        
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


# GPS Removed sub-steps
GPS_REMOVED_EXPECTED_DATE = "GPS_REMOVED_EXPECTED_DATE"
GPS_REMOVED_INSTALLATION_DATE = "GPS_REMOVED_INSTALLATION_DATE"
GPS_REMOVED_LOCATION = "GPS_REMOVED_LOCATION"
GPS_REMOVED_CONTACT_CONFIRM = "GPS_REMOVED_CONTACT_CONFIRM"
GPS_REMOVED_ALTERNATE_NUMBER = "GPS_REMOVED_ALTERNATE_NUMBER"
GPS_REMOVED_AVAILABILITY_DATE = "GPS_REMOVED_AVAILABILITY_DATE"
GPS_REMOVED_ADDITIONAL_INFO = "GPS_REMOVED_ADDITIONAL_INFO"


def handle_gps_removed_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle GPS Removed flow with LLM-driven conversational understanding.
    
    Flow:
    Q1: Temporary removal for maintenance? (LLM understands)
      - YES → Q2: Expected date → Close
      - NO → Reinstallation flow (Q3-Q7) → Service Request
    """
    context = state_manager.get_context(user_phone)
    gps_sub_step = context.get("gps_removed_sub_step")
    
    logger.info(
        f"GPS Removed Flow: Processing",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": gps_sub_step,
            "message": text_body[:50]
        }
    )
    
    # Check if user needs clarification
    if should_clarify(text_body):
        logger.info(f"GPS Removed: User needs clarification at sub_step {gps_sub_step}")
        
        context_explanation = get_context_explanation_for_step(current_step, gps_sub_step)
        current_question = get_current_question_text(current_step, gps_sub_step)
        
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    
    if current_step == ConversationStep.GPS_REMOVED_REINSTALL_DATE.value:
        
        # Q2: Expected operational date (after YES - temporary removal)
        if gps_sub_step == GPS_REMOVED_EXPECTED_DATE:
            parsed_date, error = _validate_date(text_body)
            
            if error:
                return f"⚠️ {error}"
            
            if parsed_date < date.today():
                return (
                    "⚠️ Purani date nahi select kar sakte.\n"
                    "Kripya aaj ya future ki date dein.\n\n"
                    "Example: 20-06-2026"
                )
            
            expected_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"GPS Removed: Temp removal case closed, date {expected_date_str}")
            
            state_manager.update_context(user_phone, {
                "gps_removed_expected_date": expected_date_str,
                "case_status": "CLOSED"
            })
            
            state_manager.clear_state(user_phone)
            
            return (
                "✅ Dhanyavaad.\n\n"
                "Humne note kar liya hai ki GPS device maintenance ke liye remove kiya gaya hai.\n\n"
                f"Expected operational date: 📅 {expected_date_str}\n\n"
                "Is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                "Agar GPS dobara operational hone ke baad bhi issue rahta hai, to aap support request raise kar sakte hain.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: Closed"
            )
        
        # Q3: Installation date (after NO - needs reinstallation)
        if gps_sub_step == GPS_REMOVED_INSTALLATION_DATE:
            parsed_date, error = _validate_date(text_body)
            
            if error:
                return f"⚠️ {error}"
            
            if parsed_date < date.today():
                return (
                    "⚠️ Purani date nahi select kar sakte.\n"
                    "Kripya aaj ya future ki date dein.\n\n"
                    "Example: 20-06-2026"
                )
            
            installation_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"GPS Removed: Installation date {installation_date_str}")
            state_manager.update_context(user_phone, {
                "gps_removed_installation_date": installation_date_str,
                "gps_removed_sub_step": GPS_REMOVED_LOCATION
            })
            
            return (
                "Vehicle ki current location kya hai?\n\n"
                "📍 Current Vehicle Location"
            )
        
        # Q4: Location
        if gps_sub_step == GPS_REMOVED_LOCATION:
            if len(text_body.strip()) < 5:
                return "⚠️ Kripya pura address dein."
            
            logger.info(f"GPS Removed: Location saved")
            state_manager.update_context(user_phone, {
                "gps_removed_location": text_body.strip(),
                "gps_removed_sub_step": GPS_REMOVED_CONTACT_CONFIRM
            })
            
            registered_mobile = _get_registered_mobile(user_phone, db)
            
            return (
                "Humare records ke anusaar registered mobile number:\n\n"
                f"📱 {registered_mobile}\n\n"
                "Kya engineer isi number par sampark kare ya koi aur number use kare?"
            )
        
        # Q5: Contact confirmation
        if gps_sub_step == GPS_REMOVED_CONTACT_CONFIRM:
            if _wants_alternate_number(text_body):
                # User wants alternate number
                logger.info(f"GPS Removed: Requesting alternate number")
                state_manager.update_context(user_phone, {
                    "gps_removed_sub_step": GPS_REMOVED_ALTERNATE_NUMBER
                })
                
                return "Kripya alternate mobile number share karein.\n\n📱 Alternate Number"
            
            else:
                # User wants same number
                registered_mobile = _get_registered_mobile(user_phone, db)
                logger.info(f"GPS Removed: Using registered number")
                
                state_manager.update_context(user_phone, {
                    "gps_removed_contact": registered_mobile,
                    "gps_removed_sub_step": GPS_REMOVED_AVAILABILITY_DATE
                })
                
                return (
                    "Vehicle installation ke liye kab available hogi?\n\n"
                    "📅 Example: 22-06-2026"
                )
        
        # Q5b: Alternate number
        if gps_sub_step == GPS_REMOVED_ALTERNATE_NUMBER:
            if not _validate_phone(text_body):
                return "⚠️ Kripya valid mobile number dein.\n\nExample: 9876543210"
            
            logger.info(f"GPS Removed: Alternate number saved")
            state_manager.update_context(user_phone, {
                "gps_removed_contact": text_body.strip(),
                "gps_removed_sub_step": GPS_REMOVED_AVAILABILITY_DATE
            })
            
            return (
                "Vehicle installation ke liye kab available hogi?\n\n"
                "📅 Example: 22-06-2026"
            )
        
        # Q6: Availability date
        if gps_sub_step == GPS_REMOVED_AVAILABILITY_DATE:
            parsed_date, error = _validate_date(text_body)
            
            if error:
                return f"⚠️ {error}"
            
            if parsed_date < date.today():
                return (
                    "⚠️ Purani date nahi select kar sakte.\n"
                    "Kripya aaj ya future ki date dein.\n\n"
                    "Example: 22-06-2026"
                )
            
            availability_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"GPS Removed: Availability date {availability_date_str}")
            state_manager.update_context(user_phone, {
                "gps_removed_availability_date": availability_date_str,
                "gps_removed_sub_step": GPS_REMOVED_ADDITIONAL_INFO
            })
            
            return "Kya installation visit se pehle koi aur jankari share karna chahenge?"
        
        # Q7: Additional information
        if gps_sub_step == GPS_REMOVED_ADDITIONAL_INFO:
            if _has_additional_info(text_body):
                # User provided additional info
                additional_notes = text_body.strip()
                logger.info(f"GPS Removed: Creating service request with notes")
                return _create_gps_reinstallation_request(user_phone, state_manager, db, additional_notes)
            else:
                # No additional info
                logger.info(f"GPS Removed: Creating service request without notes")
                return _create_gps_reinstallation_request(user_phone, state_manager, db, None)
        
        # Q1: Initial maintenance check (LLM-driven)
        if _is_temporary_removal(text_body):
            # Temporary removal for maintenance
            logger.info(f"GPS Removed: Temporary removal (LLM confirmed)")
            state_manager.update_context(user_phone, {
                "gps_removed_sub_step": GPS_REMOVED_EXPECTED_DATE
            })
            
            return (
                "Vehicle ya GPS system dobara kab operational hoga?\n\n"
                "📅 Example: 20-06-2026"
            )
        
        else:
            # Needs reinstallation
            logger.info(f"GPS Removed: Needs reinstallation (LLM confirmed)")
            state_manager.update_context(user_phone, {
                "gps_removed_sub_step": GPS_REMOVED_INSTALLATION_DATE
            })
            
            return (
                "GPS ko dobara install kab karwana hai?\n\n"
                "📅 Preferred Installation Date\n\n"
                "Example: 20-06-2026"
            )
    
    logger.warning(f"Unknown step in GPS removed flow: {current_step}")
    return "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein."


def _create_gps_reinstallation_request(
    user_phone: str,
    state_manager: StateManager,
    db: Session,
    additional_notes: str = None
) -> str:
    """Create GPS Reinstallation Service Request."""
    try:
        context = state_manager.get_context(user_phone)
        
        installation_date = context.get("gps_removed_installation_date", "Not specified")
        vehicle_location = context.get("gps_removed_location", "Not specified")
        contact_number = context.get("gps_removed_contact", user_phone)
        availability_date = context.get("gps_removed_availability_date", installation_date)
        
        # Get vehicle number
        vehicle_number = context.get("vehicle_number")
        if not vehicle_number:
            vehicle_number = _get_vehicle_number_from_db(user_phone, db)
        if not vehicle_number:
            vehicle_number = "UNKNOWN"
        
        # Parse dates to proper format for database
        from datetime import datetime
        try:
            installation_date_obj = datetime.strptime(installation_date, "%d-%m-%Y").date() if installation_date != "Not specified" else None
            availability_date_obj = datetime.strptime(availability_date, "%d-%m-%Y").date() if availability_date != "Not specified" else None
        except:
            installation_date_obj = None
            availability_date_obj = None
        
        # Store additional notes in driver_name field (max 100 chars)
        notes_field = additional_notes[:100] if additional_notes else None
        
        # Create ticket using proper Ticket model fields
        ticket = create_service_request_ticket(
            vehicle_number=vehicle_number,
            issue_type="GPS_REINSTALLATION",
            customer_phone=user_phone,
            location=vehicle_location,
            reinstallation_date=installation_date_obj,
            vehicle_available_date=availability_date_obj,
            owner_mobile=contact_number,
            driver_name=notes_field  # Store additional notes in driver_name field
        )
        
        ticket_number = ticket.ticket_number if ticket else "N/A"
        
        logger.info(f"GPS Removed: Service request created - {ticket_number}")
        
        state_manager.update_context(user_phone, {
            "service_request_id": ticket_number,
            "case_status": "SERVICE_REQUEST_CREATED"
        })
        
        state_manager.clear_state(user_phone)
        
        return (
            "✅ Dhanyavaad.\n\n"
            "Aapki GPS Reinstallation Service Request safalta purvak create kar di gayi hai.\n\n"
            "Hamare nearest service engineer jald hi aapse sampark karenge.\n\n"
            f"📅 Installation Date: {installation_date}\n"
            f"📍 Location: {vehicle_location}\n"
            f"📱 Contact Number: {contact_number}\n\n"
            "🙏 Thank You\n\n"
            "Service Request Status: Created\n"
            f"Ticket Number: {ticket_number}"
        )
        
    except Exception as e:
        logger.error(f"GPS Removed: Failed to create service request: {str(e)}", exc_info=True)
        state_manager.clear_state(user_phone)
        
        return (
            "⚠️ Service request create karne mein error aaya.\n\n"
            "Kripya support team se sampark karein."
        )
