"""
Vehicle Standing Flow Handler

Flow:
Customer selects: Vehicle Standing
Q1: Vehicle kab se standing condition mein hai?
  - If < 48 hours → Service Request Flow (Location → Date/Time → Contact → Service Request)
  - If >= 48 hours → Ask expected running date → Close case
"""
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.clarification_handler import (
    should_clarify,
    generate_clarification_response,
    get_context_explanation_for_step,
    get_current_question_text
)

logger = logging.getLogger("app.vehicle_standing_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _parse_standing_duration(text: str) -> tuple:
    """
    Parse how long vehicle has been standing using LLM understanding.
    Returns (hours, None) if successfully parsed
    Returns (None, error_message) if parsing failed
    
    Examples:
    - "aaj se" → 12 hours (today)
    - "kal se" → 36 hours (since yesterday)
    - "1 din se" → 24 hours
    - "2 din se" → 48 hours
    - "3 din se" → 72 hours
    - "ek hafte se" → 168 hours
    """
    from app.ai.groq_llm import generate_response
    
    try:
        prompt = f"""Extract how long the vehicle has been standing (in hours).

User said: "{text}"

Examples:
- "aaj se" → 12 hours (standing since today)
- "subah se" → 8 hours
- "kal se" → 36 hours (standing since yesterday)
- "1 din se" → 24 hours
- "2 din se" → 48 hours
- "3 din se" → 72 hours
- "4 din se" → 96 hours
- "ek hafte se" → 168 hours (7 days)
- "kaafi dino se" → 120 hours (estimated 5 days)

Respond in EXACTLY this format:
HOURS: <number>

If unclear, respond with: UNCLEAR"""

        response = generate_response(prompt).strip()
        
        logger.info(f"LLM standing duration parse: '{text[:50]}' -> {response}")
        
        if "UNCLEAR" in response.upper():
            return None, "Kripya thoda clear bataiye vehicle kab se khadi hai"
        
        # Parse hours from response
        hours = None
        for line in response.split('\n'):
            if line.startswith('HOURS:'):
                hours_str = line.replace('HOURS:', '').strip()
                try:
                    hours = int(hours_str)
                except:
                    return None, "Could not parse hours"
                break
        
        if hours is None:
            return None, "Could not extract duration"
        
        return hours, None
        
    except Exception as e:
        logger.error(f"LLM standing duration parse failed: {str(e)}")
        return None, "Kripya thoda clear bataiye vehicle kab se khadi hai (Example: aaj se, kal se, 2 din se)"


def _parse_expected_running_date(text: str) -> tuple:
    """
    Parse natural language expected running date using LLM understanding.
    Returns (parsed_date, None, has_date=True) if date found
    Returns (None, None, has_date=False) if user doesn't know
    Returns (None, error_message, None) if parsing failed
    """
    from app.ai.groq_llm import generate_response
    
    normalized = _normalize_text(text)
    
    # Check if user doesn't know
    dont_know_keywords = [
        "pata nahi", "nahi pata", "confirm nahi", "nahi hai",
        "don't know", "not sure", "uncertain", "abhi nahi pata",
        "driver batayega", "fix nahi", "decide nahi"
    ]
    
    if any(keyword in normalized for keyword in dont_know_keywords):
        logger.info(f"User doesn't know expected date: '{text[:50]}'")
        return None, None, False
    
    try:
        # Get current date for reference
        today = date.today()
        current_year = today.year
        
        prompt = f"""Extract expected running date from natural language.

Today's date: {today.strftime('%d/%m/%Y')} ({today.strftime('%A')})

User said: "{text}"

Examples:
- "kal" → Tomorrow
- "2 din baad" → Day after tomorrow
- "agle hafte" → Next week Monday
- "Monday" → Next Monday
- "25 June" → 25/06/{current_year}
- "pata nahi" → NO_DATE_AVAILABLE

If user says they don't know or are uncertain, respond with: NO_DATE_AVAILABLE

Otherwise respond in EXACTLY this format:
DATE: DD/MM/YYYY

If no clear date can be determined, respond with: UNCLEAR"""

        response = generate_response(prompt).strip()
        
        logger.info(f"LLM date parse: '{text[:50]}' -> {response}")
        
        # Check responses
        if "NO_DATE_AVAILABLE" in response.upper():
            return None, None, False
        
        if "UNCLEAR" in response.upper():
            return None, "Kripya thoda clear bataiye vehicle kab tak operational ho sakti hai", None
        
        # Parse LLM response
        date_str = None
        for line in response.split('\n'):
            if line.startswith('DATE:'):
                date_str = line.replace('DATE:', '').strip()
                break
        
        if not date_str:
            return None, "Could not parse date", None
        
        # Parse date
        try:
            parsed_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except:
            try:
                parsed_date = datetime.strptime(date_str, "%d-%m-%Y").date()
            except:
                return None, "Invalid date format from LLM", None
        
        # Validate date is not in past
        if parsed_date < today:
            return None, "Purani date nahi select kar sakte", None
        
        return parsed_date, None, True
        
    except Exception as e:
        logger.error(f"LLM date parse failed: {str(e)}")
        # Check if it's a "don't know" response
        if any(keyword in normalized for keyword in dont_know_keywords):
            return None, None, False
        return None, "Kripya date thoda clear format mein bataiye (Example: kal, 2 din baad, 25 June)", None


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


# Vehicle Standing sub-steps
VS_EXPECTED_DATE = "VS_EXPECTED_DATE"  # For >= 48 hours case
VS_LOCATION = "VS_LOCATION"  # For < 48 hours case
VS_VISIT_DATETIME = "VS_VISIT_DATETIME"
VS_CONTACT_CONFIRM = "VS_CONTACT_CONFIRM"


def handle_vehicle_standing_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle Vehicle Standing flow with LLM-driven conversational understanding.
    
    Flow:
    Q1: Vehicle kab se standing condition mein hai?
      - If < 48 hours → Service Request Flow (Location → Date/Time → Contact → Service Request)
      - If >= 48 hours → Ask expected running date → Close case
    """
    context = state_manager.get_context(user_phone)
    vs_sub_step = context.get("vs_sub_step")
    
    logger.info(
        f"Vehicle Standing Flow: Processing",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": vs_sub_step,
            "message": text_body[:50]
        }
    )
    
    # Check if user needs clarification
    if should_clarify(text_body):
        logger.info(f"Vehicle Standing: User needs clarification at sub_step {vs_sub_step}")
        
        # Provide context-specific clarification
        if vs_sub_step == VS_EXPECTED_DATE:
            context_explanation = (
                "Hum pooch rahe hain ki vehicle lagbhag kab dobara chalne lagegi. "
                "Isse humein samajhne mein madad milti hai ki GPS issue vehicle standing hone ki wajah se hai "
                "ya kisi technical issue ki wajah se."
            )
            current_question = "Kripya bata dijiye vehicle kab tak dobara operational ho sakti hai?"
        elif vs_sub_step == VS_LOCATION:
            context_explanation = (
                "Hum vehicle ki location isliye pooch rahe hain taaki service engineer ko pata rahe "
                "kahan aana hai GPS check karne ke liye."
            )
            current_question = "Vehicle ki current location kya hai?"
        elif vs_sub_step == VS_VISIT_DATETIME:
            context_explanation = (
                "Hum pooch rahe hain ki inspection ke liye vehicle kab available rahegi "
                "taaki service engineer ki visit schedule kar sakein."
            )
            current_question = "Vehicle inspection ke liye kab available rahegi?"
        elif vs_sub_step == VS_CONTACT_CONFIRM:
            context_explanation = (
                "Hum confirm kar rahe hain ki kis number par aapse contact karna hai "
                "service engineer ke visit ke liye."
            )
            current_question = "Kis number par aapse contact karna hai?"
        else:
            context_explanation = (
                "Hum pooch rahe hain ki vehicle kab se standing condition mein hai. "
                "Isse hum decide kar sakte hain ki service engineer ki zarurat hai ya nahi."
            )
            current_question = "Vehicle kab se standing condition mein hai?"
        
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    
    if current_step == ConversationStep.VEHICLE_STANDING_DURATION.value:
        
        # Q2 (>= 48 hours): Expected running date
        if vs_sub_step == VS_EXPECTED_DATE:
            parsed_date, error, has_date = _parse_expected_running_date(text_body)
            
            # Error in parsing
            if error:
                return f"⚠️ {error}"
            
            # User doesn't know the date
            if has_date is False:
                logger.info(f"Vehicle Standing: User doesn't know date - closing case")
                
                state_manager.update_context(user_phone, {
                    "standing_status": "MORE_THAN_48_HOURS_NO_DATE",
                    "case_status": "CLOSED"
                })
                
                state_manager.clear_state(user_phone)
                
                return (
                    "Koi baat nahi. 😊\n\n"
                    "Jab vehicle dobara operational ho jaye aur GPS issue continue rahe, "
                    "to aap humse sampark kar sakte hain.\n\n"
                    "Humne note kar liya hai ki vehicle 48 ghante se adhik samay se standing condition mein hai.\n\n"
                    "Is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                    "🙏 Thank You\n\n"
                    "Case Status: Closed"
                )
            
            # User provided expected date
            if parsed_date:
                expected_date_str = parsed_date.strftime("%d-%m-%Y")
                
                logger.info(f"Vehicle Standing: Expected date {expected_date_str} - closing case")
                
                state_manager.update_context(user_phone, {
                    "standing_expected_date": expected_date_str,
                    "standing_status": "MORE_THAN_48_HOURS",
                    "case_status": "CLOSED"
                })
                
                state_manager.clear_state(user_phone)
                
                return (
                    "✅ Dhanyavaad.\n\n"
                    "Humne note kar liya hai ki vehicle 48 ghante se adhik samay se standing condition mein hai.\n\n"
                    f"Expected operational date: 📅 {expected_date_str}\n\n"
                    "Is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                    "Agar vehicle dobara chalne ke baad bhi GPS issue rahta hai, "
                    "to aap support request raise kar sakte hain.\n\n"
                    "🙏 Thank You\n\n"
                    "Case Status: Closed"
                )
        
        # Q2 (< 48 hours): Location
        if vs_sub_step == VS_LOCATION:
            if len(text_body.strip()) < 5:
                return "⚠️ Kripya pura address dein."
            
            logger.info(f"Vehicle Standing: Location saved")
            state_manager.update_context(user_phone, {
                "vs_location": text_body.strip(),
                "vs_sub_step": VS_VISIT_DATETIME
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
        
        # Q3 (< 48 hours): Visit date/time
        if vs_sub_step == VS_VISIT_DATETIME:
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
            
            logger.info(f"Vehicle Standing: Visit scheduled for {visit_date_str} {visit_time_str}")
            
            state_manager.update_context(user_phone, {
                "vs_visit_date": visit_date_str,
                "vs_visit_time": visit_time_str,
                "vs_sub_step": VS_CONTACT_CONFIRM
            })
            
            registered_mobile = _get_registered_mobile(user_phone, db)
            
            return (
                "Humare records ke anusaar registered mobile number:\n\n"
                f"📱 {registered_mobile}\n\n"
                "Agar isi number par sampark karna hai to \"Theek Hai\" likhein.\n"
                "Agar koi doosra number use karna hai to woh number bhej dijiye."
            )
        
        # Q4 (< 48 hours): Contact confirmation
        if vs_sub_step == VS_CONTACT_CONFIRM:
            if _wants_same_contact(text_body):
                # Use registered number
                registered_mobile = _get_registered_mobile(user_phone, db)
                logger.info(f"Vehicle Standing: Using registered number")
                
                state_manager.update_context(user_phone, {
                    "vs_contact_number": registered_mobile
                })
            else:
                # Validate as phone number
                if not _validate_phone(text_body):
                    return (
                        "⚠️ Kripya valid mobile number dein.\n\n"
                        "Example: 9876543210 or +919876543210"
                    )
                
                logger.info(f"Vehicle Standing: Using alternate number")
                state_manager.update_context(user_phone, {
                    "vs_contact_number": text_body.strip()
                })
            
            # Create service request
            logger.info(f"Vehicle Standing: Creating service request")
            return _create_vehicle_standing_service_request(user_phone, state_manager, db)
        
        # Q1: Initial standing duration question
        hours, error = _parse_standing_duration(text_body)
        
        if error:
            return f"⚠️ {error}"
        
        logger.info(f"Vehicle Standing: Duration {hours} hours")
        
        # Store standing duration
        state_manager.update_context(user_phone, {
            "standing_hours": hours
        })
        
        # Check if >= 48 hours (2 days)
        if hours >= 48:
            logger.info(f"Vehicle Standing: >= 48 hours - asking expected date")
            state_manager.update_context(user_phone, {
                "vs_sub_step": VS_EXPECTED_DATE
            })
            
            return (
                "Samajh gaya. 🙏\n\n"
                "Vehicle ko dobara chalne mein lagbhag kitna samay lag sakta hai?\n\n"
                "📅 Example:\n"
                "• Kal\n"
                "• 2 din baad\n"
                "• Agle hafte\n"
                "• 25 June\n"
                "• Pata nahi"
            )
        else:
            logger.info(f"Vehicle Standing: < 48 hours - starting service request flow")
            state_manager.update_context(user_phone, {
                "vs_sub_step": VS_LOCATION
            })
            
            return (
                "Samajh gaya. 🙏\n\n"
                "Vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
                "📍 Example: Kirti Nagar, Delhi"
            )
    
    logger.warning(f"Unknown step in vehicle standing flow: {current_step}")
    return "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein."


def _create_vehicle_standing_service_request(
    user_phone: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """Create service request for Vehicle Standing (< 48 hours)."""
    logger.info(
        f"Vehicle Standing: Starting service request creation",
        extra={"phone": user_phone}
    )
    
    try:
        from app.services.ticket_service import create_service_request_ticket
        
        context = state_manager.get_context(user_phone)
        
        location = context.get("vs_location", "Not specified")
        visit_date = context.get("vs_visit_date", "Not specified")
        visit_time = context.get("vs_visit_time", "Not specified")
        contact_number = context.get("vs_contact_number", user_phone)
        standing_hours = context.get("standing_hours", 0)
        
        logger.info(
            f"Vehicle Standing: Gathered context",
            extra={
                "location": location[:50] if location else "None",
                "visit_date": visit_date,
                "visit_time": visit_time,
                "contact": contact_number,
                "standing_hours": standing_hours
            }
        )
        
        # Get vehicle number
        vehicle_number = context.get("vehicle_number")
        if not vehicle_number:
            logger.info(f"Vehicle Standing: No vehicle in context, querying DB")
            vehicle_number = _get_vehicle_number_from_db(user_phone, db)
        if not vehicle_number:
            logger.warning(f"Vehicle Standing: No vehicle number found, using UNKNOWN")
            vehicle_number = "UNKNOWN"
        
        logger.info(f"Vehicle Standing: Using vehicle number: {vehicle_number}")
        
        # Parse visit_date and visit_time to proper formats
        try:
            visit_date_obj = datetime.strptime(visit_date, "%d-%m-%Y").date()
            visit_time_obj = datetime.strptime(visit_time, "%H:%M").time()
        except:
            visit_date_obj = None
            visit_time_obj = None
        
        # Store standing duration in driver_name field for reference
        standing_info = f"Standing {standing_hours}hrs"[:100]
        
        logger.info(f"Vehicle Standing: Calling create_service_request_ticket")
        
        # Create ticket
        try:
            ticket = create_service_request_ticket(
                vehicle_number=vehicle_number,
                issue_type="VEHICLE_STANDING_GPS_NOT_UPDATING",
                customer_phone=user_phone,
                location=location,
                inspection_date=visit_date_obj,
                inspection_time=visit_time_obj,
                owner_mobile=contact_number,
                driver_name=standing_info
            )
            
            if not ticket:
                logger.error(f"Vehicle Standing: create_service_request_ticket returned None")
                raise Exception("Ticket creation returned None")
            
            ticket_number = ticket.ticket_number
            logger.info(f"Vehicle Standing: Ticket created successfully - {ticket_number}")
            
        except Exception as ticket_error:
            logger.error(
                f"Vehicle Standing: Ticket creation failed",
                exc_info=True,
                extra={
                    "error": str(ticket_error),
                    "vehicle_number": vehicle_number,
                    "issue_type": "VEHICLE_STANDING_GPS_NOT_UPDATING"
                }
            )
            raise
        
        state_manager.update_context(user_phone, {
            "service_request_id": ticket_number,
            "case_status": "SERVICE_REQUEST_CREATED",
            "conversation_complete": True
        })
        
        logger.info(f"Vehicle Standing: Clearing state after successful creation")
        state_manager.clear_state(user_phone)
        
        return (
            "✅ Dhanyavaad.\n\n"
            "Aapki service request safalta purvak create kar di gayi hai.\n\n"
            "*Issue:* Vehicle Standing - GPS Not Updating\n\n"
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
            f"Vehicle Standing: CRITICAL - Failed to create service request",
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
