"""
GPS Removed Flow Handler

Flow:
Customer selects: 4️⃣ GPS Removed
Q1: Maintenance/Repair confirmation (Yes/No)
  - YES → Q2: Expected date → Close Case
  - NO → GPS Reinstallation Flow (Q3-Q7) → Service Request
"""
import logging
import re
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.ticket_service import create_service_request_ticket

logger = logging.getLogger("app.gps_removed_flow")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    """Check if response is affirmative - supports natural language"""
    normalized = _normalize_text(text)
    affirmative_patterns = [
        "haan", "haa", "yes", "y", "h", "1", "हाँ", "हां",
        "maintenance", "repair", "service", "testing",
        "maintenance ke liye", "service ke liye", "repair ke liye",
        "testing ke liye", "nikala hai", "remove kiya hai",
        "isi number par", "same number", "yes this number",
        "haan kuch information", "information deni hai"
    ]
    
    # Check if it's numeric "1"
    if normalized == "1":
        return True
    
    # Check if any affirmative pattern is in the text
    return any(pattern in normalized for pattern in affirmative_patterns)


def _is_negative(text: str) -> bool:
    """Check if response is negative - supports natural language"""
    normalized = _normalize_text(text)
    negative_patterns = [
        "nahi", "na", "no", "nahin", "n", "2", "नहीं",
        "chori", "stolen", "theft",
        "dobara lagwana", "reinstall", "install karna",
        "remove ho gaya", "nikal gaya", "detach ho gaya",
        "dusra number", "doosra number", "alternate number",
        "another number", "different number"
    ]
    
    # Check if it's numeric "2"
    if normalized == "2":
        return True
    
    # Check for maintenance/service patterns - if found, NOT negative
    if any(word in normalized for word in ["maintenance", "repair", "service", "testing"]):
        return False
    
    # Check if any negative pattern is in the text
    return any(pattern in normalized for pattern in negative_patterns)


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
            logger.warning(f"No user found for phone {user_phone}")
            return None
        
        vehicle = db.query(Vehicle).filter(
            (Vehicle.manager_id == user.id) |
            (Vehicle.supervisor_id == user.id) |
            (Vehicle.driver_id == user.id)
        ).first()
        
        if vehicle:
            logger.info(f"Found vehicle {vehicle.vehicle_number} for user {user_phone}")
            return vehicle.vehicle_number
        else:
            logger.warning(f"No vehicle found for user {user_phone}")
            return None
    except Exception as e:
        logger.error(f"Error getting vehicle number: {str(e)}")
        return None


# GPS Removed sub-steps stored in context
GPS_REMOVED_EXPECTED_DATE = "GPS_REMOVED_EXPECTED_DATE"
GPS_REMOVED_INSTALLATION_DATE = "GPS_REMOVED_INSTALLATION_DATE"
GPS_REMOVED_LOCATION = "GPS_REMOVED_LOCATION"
GPS_REMOVED_CONTACT_CONFIRM = "GPS_REMOVED_CONTACT_CONFIRM"
GPS_REMOVED_ALTERNATE_NUMBER = "GPS_REMOVED_ALTERNATE_NUMBER"
GPS_REMOVED_AVAILABILITY_DATE = "GPS_REMOVED_AVAILABILITY_DATE"
GPS_REMOVED_ADDITIONAL_INFO = "GPS_REMOVED_ADDITIONAL_INFO"
GPS_REMOVED_ADDITIONAL_NOTES = "GPS_REMOVED_ADDITIONAL_NOTES"


def handle_gps_removed_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle GPS Removed flow.
    
    Flow:
    Q1: Maintenance/Repair confirmation (Yes/No)
      - YES → Q2: Expected date → Close
      - NO → Reinstallation Flow → Service Request
    
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
    context = state_manager.get_context(user_phone)
    gps_sub_step = context.get("gps_removed_sub_step")
    
    logger.info(
        f"GPS Removed Flow: Processing message",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": gps_sub_step,
            "message_preview": text_body[:50]
        }
    )
    
    # Main step: GPS_REMOVED_REINSTALL_DATE handles all sub-steps
    if current_step == ConversationStep.GPS_REMOVED_REINSTALL_DATE.value:
        
        # Q2: Expected operational date (after YES to Q1)
        if gps_sub_step == GPS_REMOVED_EXPECTED_DATE:
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
            
            expected_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"GPS Removed: Maintenance case closed with expected date {expected_date_str} for {user_phone}")
            
            # Store final data
            state_manager.update_context(user_phone, {
                "gps_removed_expected_date": expected_date_str,
                "case_status": "CLOSED"
            })
            
            # Clear state (conversation complete)
            state_manager.clear_state(user_phone)
            
            return (
                "✅ Dhanyavaad.\n\n"
                "Humne note kar liya hai ki GPS device maintenance ke liye remove kiya gaya hai.\n\n"
                f"Expected operational date: 📅 *{expected_date_str}*\n\n"
                "Is wajah se GPS inactive hona expected hai aur is samay kisi service engineer ki avashyakta nahi hai.\n\n"
                "Agar GPS dobara operational hone ke baad bhi issue rahta hai, to aap support request raise kar sakte hain.\n\n"
                "🙏 Thank You\n\n"
                "Case Status: *Closed*"
            )
        
        # Q3: Preferred Installation Date (after NO to Q1)
        if gps_sub_step == GPS_REMOVED_INSTALLATION_DATE:
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
            
            installation_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"GPS Removed: Installation date saved for {user_phone}")
            state_manager.update_context(user_phone, {
                "gps_removed_installation_date": installation_date_str,
                "gps_removed_sub_step": GPS_REMOVED_LOCATION
            })
            
            return (
                "Vehicle ki current location kya hai?\n\n"
                "📍 Current Vehicle Location\n\n"
                "Kripya pura address dein."
            )
        
        # Q4: Current Vehicle Location
        if gps_sub_step == GPS_REMOVED_LOCATION:
            if len(text_body.strip()) < 5:
                return (
                    "⚠️ Kripya pura address dein.\n\n"
                    "Example: Shop No. 5, Main Road, Mumbai - 400001"
                )
            
            logger.info(f"GPS Removed: Location saved for {user_phone}")
            state_manager.update_context(user_phone, {
                "gps_removed_location": text_body.strip(),
                "gps_removed_sub_step": GPS_REMOVED_CONTACT_CONFIRM
            })
            
            # Get registered mobile number
            registered_mobile = _get_registered_mobile(user_phone, db)
            
            return (
                "Humare records ke anusaar aapka registered mobile number hai:\n\n"
                f"📱 *{registered_mobile}*\n\n"
                "Kya isi number par service engineer sampark kare?\n\n"
                "1️⃣ Haan, isi number par\n"
                "2️⃣ Nahi, doosra number dena hai"
            )
        
        # Q5: Contact number confirmation
        if gps_sub_step == GPS_REMOVED_CONTACT_CONFIRM:
            if _is_affirmative(text_body):
                # Use existing registered number
                registered_mobile = _get_registered_mobile(user_phone, db)
                logger.info(f"GPS Removed: Using registered number for {user_phone}")
                
                state_manager.update_context(user_phone, {
                    "gps_removed_contact": registered_mobile,
                    "gps_removed_sub_step": GPS_REMOVED_AVAILABILITY_DATE
                })
                
                return (
                    "Vehicle GPS installation ke liye kab available hogi?\n\n"
                    "📅 Expected Availability Date\n\n"
                    "(Example: 22-06-2026)"
                )
            
            elif _is_negative(text_body):
                # Ask for alternate number
                logger.info(f"GPS Removed: Requesting alternate number for {user_phone}")
                state_manager.update_context(user_phone, {
                    "gps_removed_sub_step": GPS_REMOVED_ALTERNATE_NUMBER
                })
                
                return (
                    "Kripya alternative mobile number share karein.\n\n"
                    "📱 Alternate Mobile Number\n\n"
                    "Example: +919876543210 or 9876543210"
                )
            
            else:
                # Invalid response - show options again
                return (
                    "⚠️ Kripya niche diye gaye options mein se ek chunen:\n\n"
                    "1️⃣ Haan, isi number par\n"
                    "2️⃣ Nahi, doosra number dena hai"
                )
        
        # Q5b: Alternate number input
        if gps_sub_step == GPS_REMOVED_ALTERNATE_NUMBER:
            if not _validate_phone(text_body):
                return (
                    "⚠️ Kripya sahi mobile number dein.\n\n"
                    "Example: +919876543210 or 9876543210"
                )
            
            logger.info(f"GPS Removed: Alternate number saved for {user_phone}")
            state_manager.update_context(user_phone, {
                "gps_removed_contact": text_body.strip(),
                "gps_removed_sub_step": GPS_REMOVED_AVAILABILITY_DATE
            })
            
            return (
                "Vehicle GPS installation ke liye kab available hogi?\n\n"
                "📅 Expected Availability Date\n\n"
                "(Example: 22-06-2026)"
            )
        
        # Q6: Vehicle availability date
        if gps_sub_step == GPS_REMOVED_AVAILABILITY_DATE:
            parsed_date, error = _validate_date(text_body)
            
            if error:
                return f"⚠️ {error}"
            
            # Check if date is not in the past
            if parsed_date < date.today():
                return (
                    "⚠️ Purani date nahi select kar sakte.\n"
                    "Kripya aaj ya future ki date dein.\n\n"
                    "Example: 22-06-2026"
                )
            
            expected_date_str = parsed_date.strftime("%d-%m-%Y")
            
            logger.info(f"GPS Removed: Availability date saved for {user_phone}")
            state_manager.update_context(user_phone, {
                "gps_removed_availability_date": expected_date_str,
                "gps_removed_sub_step": GPS_REMOVED_ADDITIONAL_INFO
            })
            
            return (
                "Hum GPS re-installation ke liye nearest service engineer assign karne ja rahe hain.\n\n"
                "Kya aap humein koi additional information dena chahte hain?\n\n"
                "1️⃣ Yes\n"
                "2️⃣ No"
            )
        
        # Q7: Additional information
        if gps_sub_step == GPS_REMOVED_ADDITIONAL_INFO:
            if _is_affirmative(text_body):
                # Ask for additional notes
                logger.info(f"GPS Removed: Requesting additional notes for {user_phone}")
                state_manager.update_context(user_phone, {
                    "gps_removed_sub_step": GPS_REMOVED_ADDITIONAL_NOTES
                })
                
                return (
                    "Kripya apni additional information share karein.\n\n"
                    "📝 Additional Notes"
                )
            
            elif _is_negative(text_body):
                # No additional info - create service request
                logger.info(f"GPS Removed: No additional info - creating service request for {user_phone}")
                return _create_gps_reinstallation_request(user_phone, state_manager, db, None)
            
            else:
                # Invalid response - show options again
                return (
                    "⚠️ Kripya niche diye gaye options mein se ek chunen:\n\n"
                    "1️⃣ Yes\n"
                    "2️⃣ No"
                )
        
        # Q7b: Additional notes input
        if gps_sub_step == GPS_REMOVED_ADDITIONAL_NOTES:
            additional_notes = text_body.strip()
            logger.info(f"GPS Removed: Additional notes '{additional_notes[:50]}...' - creating service request for {user_phone}")
            
            try:
                result = _create_gps_reinstallation_request(user_phone, state_manager, db, additional_notes)
                logger.info(f"GPS Removed: Service request function returned successfully for {user_phone}")
                return result
            except Exception as e:
                logger.error(f"GPS Removed: Exception in creating service request: {str(e)}", exc_info=True)
                state_manager.clear_state(user_phone)
                return (
                    "⚠️ Service request create karne mein technical error aaya.\n"
                    "⚠️ Technical error creating service request.\n\n"
                    f"Error: {str(e)}\n\n"
                    "Kripya support team se sampark karein.\n"
                    "Please contact support team."
                )
        
        # Q1: Initial maintenance/repair confirmation
        if _is_affirmative(text_body):
            # YES - Maintenance/repair - ask for expected date
            logger.info(f"GPS Removed: YES (Maintenance) - asking expected date for {user_phone}")
            state_manager.update_context(user_phone, {"gps_removed_sub_step": GPS_REMOVED_EXPECTED_DATE})
            return (
                "Dhanyavaad. 🙏\n\n"
                "Vehicle ya GPS system dobara kab operational hoga?\n\n"
                "📅 Expected Running Date\n\n"
                "(Example: 20-06-2026)"
            )
        
        elif _is_negative(text_body):
            # NO - Not maintenance - start reinstallation flow
            logger.info(f"GPS Removed: NO (Not maintenance) - starting reinstallation flow for {user_phone}")
            state_manager.update_context(user_phone, {"gps_removed_sub_step": GPS_REMOVED_INSTALLATION_DATE})
            return (
                "GPS ko dobara install kab karwana hai?\n\n"
                "📅 Preferred Installation Date\n\n"
                "(Example: 20-06-2026)"
            )
        
        else:
            # Invalid response
            return (
                "⚠️ Kripya valid option select karein.\n\n"
                "Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?\n\n"
                "1️⃣ Yes\n"
                "2️⃣ No"
            )
    
    # Unknown step
    logger.warning(f"Unknown step in GPS removed flow: {current_step}")
    return (
        "⚠️ Kuch galat ho gaya. Kripya 'reset' type karein.\n"
        "⚠️ Something went wrong. Please type 'reset'."
    )


def _create_gps_reinstallation_request(
    user_phone: str,
    state_manager: StateManager,
    db: Session,
    additional_notes: str = None
) -> str:
    """
    Create GPS Reinstallation Service Request.
    
    Args:
        user_phone: User's phone number
        state_manager: StateManager instance
        db: Database session
        additional_notes: Optional additional information from customer
        
    Returns:
        Final confirmation message
    """
    try:
        context = state_manager.get_context(user_phone)
        
        # Retrieve all collected information
        installation_date = context.get("gps_removed_installation_date", "Not specified")
        vehicle_location = context.get("gps_removed_location", "Not specified")
        contact_number = context.get("gps_removed_contact", user_phone)
        availability_date = context.get("gps_removed_availability_date", installation_date)
        
        # Get vehicle number from context or database
        vehicle_number = context.get("vehicle_number")
        if not vehicle_number:
            vehicle_number = _get_vehicle_number_from_db(user_phone, db)
        
        if not vehicle_number:
            logger.error(f"GPS Removed: No vehicle number found for {user_phone}")
            vehicle_number = "UNKNOWN"
        
        # Build issue description
        issue_description = f"GPS Reinstallation Request\n"
        issue_description += f"Preferred Installation Date: {installation_date}\n"
        issue_description += f"Vehicle Location: {vehicle_location}\n"
        issue_description += f"Contact Number: {contact_number}\n"
        issue_description += f"Vehicle Available Date: {availability_date}"
        
        if additional_notes:
            issue_description += f"\n\nAdditional Information:\n{additional_notes}"
        
        # Create service request ticket
        ticket = create_service_request_ticket(
            vehicle_number=vehicle_number,
            issue_type="GPS_REINSTALLATION",
            customer_phone=user_phone,
            issue_description=issue_description,
            priority="MEDIUM"
        )
        
        ticket_number = ticket.ticket_number if ticket else "N/A"
        
        logger.info(
            f"GPS Removed: Service request created",
            extra={
                "phone": user_phone,
                "ticket": ticket_number,
                "installation_date": installation_date,
                "location": vehicle_location
            }
        )
        
        # Store ticket in context
        state_manager.update_context(user_phone, {
            "service_request_id": ticket_number,
            "case_status": "SERVICE_REQUEST_CREATED",
            "conversation_complete": True  # Mark as complete but don't clear yet
        })
        
        # Build final message
        message = (
            "✅ Dhanyavaad.\n\n"
            "Aapki GPS Reinstallation Service Request safalta purvak create kar di gayi hai.\n\n"
            "Hamare nearest service engineer jald hi aapse sampark karenge.\n\n"
            "🙏 Thank You\n\n"
            "*Service Request Status:* Created\n"
            f"*Ticket Number:* {ticket_number}"
        )
        
        # Clear state AFTER building message (will be cleared after message is sent)
        state_manager.clear_state(user_phone)
        
        return message
        
    except Exception as e:
        logger.error(
            f"GPS Removed: Failed to create service request: {str(e)}",
            exc_info=True,
            extra={"phone": user_phone}
        )
        
        # Clear state on error
        state_manager.clear_state(user_phone)
        
        return (
            "⚠️ Service request create karne mein error aaya.\n"
            "⚠️ Error creating service request.\n\n"
            "Kripya support team se sampark karein.\n"
            "Please contact support team."
        )
