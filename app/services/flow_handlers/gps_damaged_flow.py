"""
GPS Damaged Flow Handler

Flow:
Customer selects: GPS Damaged
Q1: Current location (where inspection is needed)
Q2: Visit date/time (natural language accepted)
Q3: Contact confirmation (LLM-driven)
Q4: Optional additional info
→ Service Request Created
"""
import logging
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.ticket_service import create_service_request_ticket

logger = logging.getLogger("app.gps_damaged_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _parse_natural_datetime(text: str) -> tuple:
    """
    Parse natural language date/time using LLM understanding.
    Returns (parsed_date, parsed_time, None) if valid, (None, None, error_message) if invalid.
    """
    from app.ai.groq_llm import generate_response
    
    try:
        # Get current date for reference
        today = date.today()
        current_year = today.year
        
        prompt = f"""Convert this natural language date/time into structured format.

Today's date: {today.strftime('%d/%m/%Y')} ({today.strftime('%A')})

User said: "{text}"

Examples:
- "kal subah" → Tomorrow 10:00 AM
- "aaj shaam" → Today 06:00 PM
- "22 June" → 22/06/{current_year} 10:00 AM
- "Monday afternoon" → Next Monday 02:00 PM
- "22 June 10 baje" → 22/06/{current_year} 10:00 AM
- "agle hafte" → Next week Monday 10:00 AM

Respond in EXACTLY this format:
DATE: DD/MM/YYYY
TIME: HH:MM

If time not specified, use 10:00 for morning, 14:00 for afternoon, 18:00 for evening."""

        response = generate_response(prompt).strip()
        
        logger.info(f"LLM date/time parse: '{text[:50]}' -> {response[:100]}")
        
        # Parse LLM response
        lines = response.split('\n')
        date_str = None
        time_str = None
        
        for line in lines:
            if line.startswith('DATE:'):
                date_str = line.replace('DATE:', '').strip()
            elif line.startswith('TIME:'):
                time_str = line.replace('TIME:', '').strip()
        
        if not date_str or not time_str:
            return None, None, "Could not parse date/time"
        
        # Parse date
        try:
            parsed_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except:
            try:
                parsed_date = datetime.strptime(date_str, "%d-%m-%Y").date()
            except:
                return None, None, "Invalid date format from LLM"
        
        # Parse time
        try:
            parsed_time = datetime.strptime(time_str, "%H:%M").time()
        except:
            return None, None, "Invalid time format from LLM"
        
        return parsed_date, parsed_time, None
        
    except Exception as e:
        logger.error(f"LLM date/time parse failed: {str(e)}")
        # Fallback: try standard formats
        try:
            dt = datetime.strptime(text.strip(), "%d/%m/%Y %H:%M")
            return dt.date(), dt.time(), None
        except:
            try:
                dt = datetime.strptime(text.strip(), "%d-%m-%Y %H:%M")
                return dt.date(), dt.time(), None
            except:
                return None, None, "Kripya date aur time clear format mein dein (Example: kal subah, 22 June, Monday afternoon)"


def _wants_same_contact(text: str) -> bool:
    """
    Check if user wants to use registered contact number using LLM understanding.
    Returns True if wants same contact.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for affirmative
    if any(word in normalized for word in ["theek hai", "same", "isi number", "ok", "haan"]):
        return True
    
    # Check if it looks like a phone number
    import re
    if re.match(r'^[\d\s\+\-\(\)]+$', text.strip()) and len(re.sub(r'[^\d]', '', text)) >= 10:
        return False  # It's a phone number
    
    # Use LLM for understanding
    try:
        prompt = f"""Determine if user wants to use the same registered contact number or provide a different one.

User was told: "Agar isi number par sampark karna hai to 'Theek Hai' likhein. Agar koi doosra number use karna hai to woh number bhej dijiye."

User replied: "{text}"

Examples of SAME (use registered number):
- "theek hai"
- "same number"
- "isi number par sampark karein"
- "ok"
- "haan"

Examples of DIFFERENT (user providing new number):
- "9876543210"
- "+919876543210"
- User provides a phone number

Respond with: SAME or DIFFERENT"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM contact check: '{text[:50]}' -> {response}")
        
        return response == "SAME"
        
    except Exception as e:
        logger.error(f"LLM contact check failed: {str(e)}")
        # Fallback
        return "theek" in normalized or "same" in normalized or "isi number" in normalized


def _wants_gps_installation(text: str) -> bool:
    """
    Check if user wants to proceed with GPS installation service request using LLM.
    Returns True if wants installation service.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for affirmative
    if any(word in normalized for word in ["haan", "yes", "karwana", "chahte", "continue"]):
        return True
    
    # Quick check for negative
    if any(word in normalized for word in ["nahi", "no", "nahin", "mat"]) and not any(word in normalized for word in ["engineer", "service", "bhej"]):
        return False
    
    # Use LLM for understanding
    try:
        prompt = f"""Determine if user wants to proceed with GPS installation service request.

User was asked: "Kya aap abhi GPS installation ke liye service request continue karna chahte hain?"

User replied: "{text}"

Examples of YES (wants installation):
- "haan"
- "yes"
- "karwana hai"
- "chahte hain"
- "continue karo"
- "proceed"

Examples of NO (does not want installation now):
- "nahi"
- "nahin"
- "no"
- "abhi nahi"
- "baad mein"

Respond with: YES or NO"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM installation check: '{text[:50]}' -> {response}")
        
        return response == "YES"
        
    except Exception as e:
        logger.error(f"LLM installation check failed: {str(e)}")
        # Fallback
        return "haan" in normalized or "yes" in normalized or "karwana" in normalized


def _user_changed_mind_wants_service(text: str) -> bool:
    """
    Check if user changed their mind and now wants service engineer.
    Used when user previously said NO but then asks for service.
    """
    from app.ai.groq_llm import generate_response
    
    normalized = text.strip().lower() if text else ""
    
    # Quick check for service request keywords
    service_keywords = ["engineer", "service", "bhej", "karwana", "chahiye", "installation"]
    if any(keyword in normalized for keyword in service_keywords):
        return True
    
    # Use LLM for understanding
    try:
        prompt = f"""User was asked for expected date when GPS will be running.

User replied: "{text}"

Determine if user is asking for service engineer instead of providing a date.

Examples of WANTS_SERVICE:
- "nahi service engineer bhej do"
- "engineer chahiye"
- "installation karwana hai"
- "service bhej do"
- "abhi karwana hai"

Examples of PROVIDING_DATE:
- "20-06-2026"
- "kal tak"
- "2 din mein"
- "next week"

Respond with: WANTS_SERVICE or PROVIDING_DATE"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM changed mind check: '{text[:50]}' -> {response}")
        
        return response == "WANTS_SERVICE"
        
    except Exception as e:
        logger.error(f"LLM changed mind check failed: {str(e)}")
        # Fallback
        return any(keyword in normalized for keyword in ["engineer", "service", "bhej", "karwana"])


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
    import re
    cleaned = re.sub(r'[^\d+]', '', phone)
    return len(cleaned) >= 10 and len(cleaned) <= 15


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
    """Get vehicle number from database"""
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


# GPS Damaged sub-steps
GPS_DAMAGED_CONFIRMATION = "GPS_DAMAGED_CONFIRMATION"
GPS_DAMAGED_EXPECTED_DATE = "GPS_DAMAGED_EXPECTED_DATE"
GPS_DAMAGED_LOCATION = "GPS_DAMAGED_LOCATION"
GPS_DAMAGED_VISIT_DATETIME = "GPS_DAMAGED_VISIT_DATETIME"
GPS_DAMAGED_CONTACT_CONFIRM = "GPS_DAMAGED_CONTACT_CONFIRM"
GPS_DAMAGED_ADDITIONAL_INFO = "GPS_DAMAGED_ADDITIONAL_INFO"


def handle_gps_damaged_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle GPS Damaged flow with LLM-driven conversational understanding.
    
    Flow:
    Q1: Installation confirmation
      - YES → Q2: Location → Q3: Date/Time → Q4: Contact → Q5: Additional Info → Service Request
      - NO → Q2: Expected date when GPS will be running → Close case or engineer assignment
    """
    context = state_manager.get_context(user_phone)
    gps_sub_step = context.get("gps_damaged_sub_step")
    
    logger.info(
        f"GPS Damaged Flow: Processing",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": gps_sub_step,
            "message": text_body[:50]
        }
    )
    
    if current_step == ConversationStep.GPS_DAMAGED_LOCATION.value:
        
        # Q2 (after NO): Expected date when GPS will be running
        if gps_sub_step == GPS_DAMAGED_EXPECTED_DATE:
            # First check if user changed their mind and wants service now
            if _user_changed_mind_wants_service(text_body):
                logger.info(f"GPS Damaged: User changed mind, wants service now")
                state_manager.update_context(user_phone, {
                    "gps_damaged_sub_step": GPS_DAMAGED_LOCATION
                })
                
                return (
                    "Bahut achha! 👍\n\n"
                    "Main abhi service engineer arrange kar dunga.\n\n"
                    "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
                    "📍 Example: Kirti Nagar, Delhi"
                )
            
            # Otherwise treat as date
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
            
            logger.info(f"GPS Damaged: Installation declined, expected date {expected_date_str}")
            
            state_manager.update_context(user_phone, {
                "gps_damaged_expected_date": expected_date_str,
                "case_status": "PENDING_GPS_INSTALLATION"
            })
            
            state_manager.clear_state(user_phone)
            
            return (
                "✅ Dhanyavaad.\n\n"
                "Humne note kar liya hai ki GPS device damage hai.\n\n"
                f"Expected operational date: 📅 {expected_date_str}\n\n"
                "Main aapko us date par dobara contact karunga installation ke liye.\n\n"
                "Agar us se pehle koi urgency ho ya aap ready ho jaayen, to aap hume contact kar sakte hain.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: Pending GPS Installation"
            )
        
        # Q3 (after YES): Visit date/time (natural language accepted)
        if gps_sub_step == GPS_DAMAGED_VISIT_DATETIME:
            parsed_date, parsed_time, error = _parse_natural_datetime(text_body)
            
            if error:
                return f"⚠️ {error}"
            
            if parsed_date < date.today():
                return (
                    "⚠️ Purani date nahi select kar sakte.\n"
                    "Kripya aaj ya future ki date dein.\n\n"
                    "Example: kal subah, aaj shaam, 22 June"
                )
            
            visit_date_str = parsed_date.strftime("%d-%m-%Y")
            visit_time_str = parsed_time.strftime("%H:%M")
            
            logger.info(f"GPS Damaged: Visit scheduled for {visit_date_str} {visit_time_str}")
            
            state_manager.update_context(user_phone, {
                "gps_damaged_visit_date": visit_date_str,
                "gps_damaged_visit_time": visit_time_str,
                "gps_damaged_sub_step": GPS_DAMAGED_CONTACT_CONFIRM
            })
            
            registered_mobile = _get_registered_mobile(user_phone, db)
            
            return (
                "Humare records ke anusaar registered mobile number:\n\n"
                f"📱 {registered_mobile}\n\n"
                "Agar isi number par sampark karna hai to \"Theek Hai\" likhein.\n"
                "Agar koi doosra number use karna hai to woh number bhej dijiye."
            )
        
        # Q4: Contact confirmation
        if gps_sub_step == GPS_DAMAGED_CONTACT_CONFIRM:
            if _wants_same_contact(text_body):
                # Use registered number
                registered_mobile = _get_registered_mobile(user_phone, db)
                logger.info(f"GPS Damaged: Using registered number")
                
                state_manager.update_context(user_phone, {
                    "gps_damaged_contact_number": registered_mobile,
                    "gps_damaged_sub_step": GPS_DAMAGED_ADDITIONAL_INFO
                })
            else:
                # Validate as phone number
                if not _validate_phone(text_body):
                    return (
                        "⚠️ Kripya valid mobile number dein.\n\n"
                        "Example: 9876543210 or +919876543210"
                    )
                
                logger.info(f"GPS Damaged: Using alternate number")
                state_manager.update_context(user_phone, {
                    "gps_damaged_contact_number": text_body.strip(),
                    "gps_damaged_sub_step": GPS_DAMAGED_ADDITIONAL_INFO
                })
            
            return (
                "Agar inspection visit se pehle koi aur jankari share karna chahte hain to bata sakte hain.\n\n"
                "(Yeh optional hai.)"
            )
        
        # Q5: Additional info (optional)
        if gps_sub_step == GPS_DAMAGED_ADDITIONAL_INFO:
            normalized = _normalize_text(text_body)
            
            # Check if user said no or similar
            if normalized in ["nahi", "na", "no", "nahin"]:
                additional_info = None
            elif len(text_body.strip()) > 3:
                additional_info = text_body.strip()
            else:
                additional_info = None
            
            logger.info(f"GPS Damaged: Creating service request")
            return _create_gps_damaged_service_request(user_phone, state_manager, db, additional_info)
        
        # Q1: Initial installation confirmation (or Location after confirmation)
        if gps_sub_step == GPS_DAMAGED_CONFIRMATION:
            if _wants_gps_installation(text_body):
                # User wants to proceed with installation
                logger.info(f"GPS Damaged: User confirmed installation service")
                state_manager.update_context(user_phone, {
                    "gps_damaged_sub_step": GPS_DAMAGED_LOCATION
                })
                
                return (
                    "Bahut achha! 👍\n\n"
                    "Main aage ki process complete karke service engineer arrange kar dunga.\n\n"
                    "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
                    "📍 Example: Kirti Nagar, Delhi"
                )
            else:
                # User does not want installation now
                logger.info(f"GPS Damaged: User declined installation service")
                state_manager.update_context(user_phone, {
                    "gps_damaged_sub_step": GPS_DAMAGED_EXPECTED_DATE
                })
                
                return (
                    "Theek hai, koi baat nahi.\n\n"
                    "Kripya bataiye ki GPS kab tak running ho jayega ya installation complete ho jayega?\n\n"
                    "📅 Expected Date\n\n"
                    "Example: 20-06-2026\n\n"
                    "Note: Agar aap chahein to main aapko us date par contact kar sakta hoon installation ke liye."
                )
        
        # Q2 (after YES): Location question
        if len(text_body.strip()) < 5:
            return "⚠️ Kripya pura address dein."
        
        logger.info(f"GPS Damaged: Location saved")
        state_manager.update_context(user_phone, {
            "gps_damaged_location": text_body.strip(),
            "gps_damaged_sub_step": GPS_DAMAGED_VISIT_DATETIME
        })
        
        return (
            "Dhanyavaad. 📍\n\n"
            "Vehicle inspection ke liye kab available rahegi?\n\n"
            "Aap normal language mein bata sakte hain.\n\n"
            "Examples:\n"
            "• Kal subah\n"
            "• Aaj shaam\n"
            "• 22 June\n"
            "• Monday morning"
        )
    
    logger.warning(f"Unknown step in GPS damaged flow: {current_step}")
    return "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein."


def _create_gps_damaged_service_request(
    user_phone: str,
    state_manager: StateManager,
    db: Session,
    additional_info: str = None
) -> str:
    """Create service request for GPS Damaged."""
    logger.info(
        f"GPS Damaged: Starting service request creation",
        extra={
            "phone": user_phone,
            "has_additional_info": additional_info is not None
        }
    )
    
    try:
        context = state_manager.get_context(user_phone)
        
        location = context.get("gps_damaged_location", "Not specified")
        visit_date = context.get("gps_damaged_visit_date", "Not specified")
        visit_time = context.get("gps_damaged_visit_time", "Not specified")
        contact_number = context.get("gps_damaged_contact_number", user_phone)
        
        logger.info(
            f"GPS Damaged: Gathered context",
            extra={
                "location": location[:50] if location else "None",
                "visit_date": visit_date,
                "visit_time": visit_time,
                "contact": contact_number
            }
        )
        
        # Get vehicle number
        vehicle_number = context.get("vehicle_number")
        if not vehicle_number:
            logger.info(f"GPS Damaged: No vehicle in context, querying DB")
            vehicle_number = _get_vehicle_number_from_db(user_phone, db)
        if not vehicle_number:
            logger.warning(f"GPS Damaged: No vehicle number found, using UNKNOWN")
            vehicle_number = "UNKNOWN"
        
        logger.info(f"GPS Damaged: Using vehicle number: {vehicle_number}")
        
        # Parse visit_date and visit_time to proper formats
        try:
            visit_date_obj = datetime.strptime(visit_date, "%d-%m-%Y").date()
            visit_time_obj = datetime.strptime(visit_time, "%H:%M").time()
        except:
            visit_date_obj = None
            visit_time_obj = None
        
        # Store additional info in driver_name field (max 100 chars)
        driver_notes = additional_info[:100] if additional_info else None
        
        logger.info(f"GPS Damaged: Calling create_service_request_ticket")
        
        # Create ticket with enhanced error handling
        try:
            ticket = create_service_request_ticket(
                vehicle_number=vehicle_number,
                issue_type="GPS_DAMAGED",
                customer_phone=user_phone,
                location=location,
                inspection_date=visit_date_obj,
                inspection_time=visit_time_obj,
                owner_mobile=contact_number,
                driver_name=driver_notes  # Store additional info in driver_name field
            )
            
            if not ticket:
                logger.error(f"GPS Damaged: create_service_request_ticket returned None")
                raise Exception("Ticket creation returned None")
            
            ticket_number = ticket.ticket_number
            logger.info(f"GPS Damaged: Ticket created successfully - {ticket_number}")
            
        except Exception as ticket_error:
            logger.error(
                f"GPS Damaged: Ticket creation failed",
                exc_info=True,
                extra={
                    "error": str(ticket_error),
                    "vehicle_number": vehicle_number,
                    "issue_type": "GPS_DAMAGED"
                }
            )
            raise
        
        state_manager.update_context(user_phone, {
            "service_request_id": ticket_number,
            "case_status": "SERVICE_REQUEST_CREATED",
            "conversation_complete": True
        })
        
        logger.info(f"GPS Damaged: Clearing state after successful creation")
        state_manager.clear_state(user_phone)
        
        return (
            "✅ Dhanyavaad.\n\n"
            "Aapki service request safalta purvak create kar di gayi hai.\n\n"
            "*Issue:* GPS Damaged\n\n"
            f"📍 *Location:* {location}\n"
            f"📅 *Visit Schedule:* {visit_date} at {visit_time}\n"
            f"📱 *Contact:* {contact_number}\n\n"
            "Hamare nearest service engineer jald hi aapse sampark karenge.\n\n"
            "🙏 Thank You\n\n"
            "Service Request Status: Created\n"
            f"Ticket Number: {ticket_number}"
        )
        
    except Exception as e:
        logger.error(
            f"GPS Damaged: CRITICAL - Failed to create service request",
            exc_info=True,
            extra={
                "phone": user_phone,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        state_manager.clear_state(user_phone)
        
        return (
            "⚠️ Service request create karne mein error aaya.\n\n"
            "Kripya support team se sampark karein.\n\n"
            f"Error: {str(e)[:100]}"
        )
