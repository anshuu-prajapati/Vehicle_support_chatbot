import logging
import re
import asyncio
import time
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.services.greeting_service import GreetingService
from app.services.menu_service import MenuService
from app.services.state_manager import ConversationStep, StateManager
from app.services.ticket_service import create_ticket
from app.services.whatsapp_service import send_whatsapp_message
from app.services.vehicle_status_service import VehicleStatusService
from app.db.models.vehicle import Vehicle
from app.db.models.user import User

logger = logging.getLogger("app.support_flow")


def _normalize_text(text: str) -> str:
    return text.strip().lower() if text else ""


def _is_affirmative(text: str) -> bool:
    return text in ["haan", "haa", "yes", "y", "h"]


def _is_negative(text: str) -> bool:
    return text in ["nahi", "na", "no", "nahin"]


def _normalize_phone_number(phone_input: str) -> Tuple[Optional[str], str]:
    """
    Normalize phone number to E.164 format for WhatsApp API.
    
    Args:
        phone_input: Raw phone number input from user
        
    Returns:
        Tuple of (normalized_number, error_message)
        If successful: ("+919876543210", "")
        If failed: (None, "error description")
    """
    if not phone_input:
        return None, "Phone number cannot be empty"
    
    # Clean the input - remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone_input.strip())
    
    # Log the cleaning process
    logger.info(
        "Phone number cleaning process",
        extra={
            "original_input": phone_input,
            "cleaned_input": cleaned
        }
    )
    
    # Check for completely invalid characters
    if not re.match(r'^[\+\d]+$', cleaned):
        return None, "Phone number contains invalid characters. Only numbers and + are allowed."
    
    # Handle different input formats
    if cleaned.startswith('+'):
        # Already has country code
        formatted_number = cleaned
    elif cleaned.startswith('91') and len(cleaned) == 12:
        # Indian number with country code but no +
        formatted_number = '+' + cleaned
    elif cleaned.startswith('0') and len(cleaned) == 11:
        # Indian number with leading 0 (remove 0 and add +91)
        formatted_number = '+91' + cleaned[1:]
    elif len(cleaned) == 10:
        # Indian number without country code
        formatted_number = '+91' + cleaned
    else:
        # Try to guess format
        if len(cleaned) >= 10 and len(cleaned) <= 15:
            # Assume Indian number if 10-15 digits and no country code
            if not cleaned.startswith('91'):
                formatted_number = '+91' + cleaned
            else:
                formatted_number = '+' + cleaned
        else:
            return None, f"Invalid phone number length: {len(cleaned)} digits. Expected 10-15 digits."
    
    # Validate E.164 format
    e164_pattern = r'^\+[1-9]\d{1,14}$'
    if not re.match(e164_pattern, formatted_number):
        return None, f"Phone number {formatted_number} is not in valid international format"
    
    # Additional validation for Indian numbers (most common case)
    if formatted_number.startswith('+91'):
        if len(formatted_number) != 13:  # +91 + 10 digits
            return None, f"Indian phone numbers must have exactly 10 digits after +91. Got: {len(formatted_number) - 3}"
        
        # Check if it's a valid Indian mobile number (starts with 6,7,8,9)
        first_digit = formatted_number[3]  # First digit after +91
        if first_digit not in '6789':
            logger.warning(
                "Potentially invalid Indian mobile number",
                extra={"phone_number": formatted_number, "first_digit": first_digit}
            )
    
    logger.info(
        "Phone number successfully normalized",
        extra={
            "original_input": phone_input,
            "normalized_number": formatted_number
        }
    )
    
    return formatted_number, ""


def _send_whatsapp_with_detailed_logging(phone_number: str, message: str, context: dict = None) -> Tuple[bool, str]:
    """
    Send WhatsApp message with comprehensive error handling and logging.
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        logger.info(
            "Attempting to send WhatsApp message",
            extra={
                "to_phone": phone_number,
                "message_length": len(message),
                "context": context or {}
            }
        )
        
        response = send_whatsapp_message(phone_number, message)
        
        # Log successful response
        logger.info(
            "WhatsApp message sent successfully",
            extra={
                "to_phone": phone_number,
                "response": response,
                "context": context or {}
            }
        )
        
        return True, ""
        
    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Failed to send WhatsApp message",
            extra={
                "to_phone": phone_number,
                "error": error_msg,
                "error_type": type(e).__name__,
                "context": context or {}
            },
            exc_info=True
        )
        
        # Categorize error types for better user feedback
        if "invalid number" in error_msg.lower():
            return False, "The phone number appears to be invalid or not registered with WhatsApp"
        elif "rate limit" in error_msg.lower():
            return False, "Message sending temporarily limited. Please try again in a few minutes"
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return False, "Network connection issue. Please try again"
        else:
            return False, f"Failed to send message: {error_msg}"


def _get_vehicle_number_for_user(user_phone: str, db: Session) -> Optional[str]:
    """
    Get vehicle number associated with a user (manager, supervisor, or driver).
    
    Args:
        user_phone: User's phone number
        db: Database session
        
    Returns:
        Vehicle number or None if not found
    """
    try:
        # First, get the user
        user = db.query(User).filter(User.phone_number == user_phone).first()
        if not user:
            logger.warning(f"User not found for phone: {user_phone}")
            return None
        
        # Find vehicle associated with this user (as manager, supervisor, or driver)
        vehicle = db.query(Vehicle).filter(
            (Vehicle.manager_id == user.id) |
            (Vehicle.supervisor_id == user.id) |
            (Vehicle.driver_id == user.id)
        ).first()
        
        if vehicle:
            logger.info(f"Found vehicle '{vehicle.vehicle_number}' for user {user_phone}")
            return vehicle.vehicle_number
        
        logger.warning(f"No vehicle found for user {user_phone}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting vehicle number for user {user_phone}: {str(e)}")
        return None


def _capture_baseline_gps_coordinates(user_phone: str, vehicle_number: str, db: Session, state_manager: StateManager) -> bool:
    """
    Capture baseline GPS coordinates at the start of GPS repair process.
    
    Args:
        user_phone: User's phone number
        vehicle_number: Vehicle registration number
        db: Database session
        state_manager: State manager instance
        
    Returns:
        True if baseline captured successfully, False otherwise
    """
    try:
        logger.info(
            f"Capturing baseline GPS coordinates for vehicle {vehicle_number}",
            extra={"user_phone": user_phone, "vehicle_number": vehicle_number}
        )
        
        # Get current vehicle status
        status_service = VehicleStatusService(db)
        vehicle_status = status_service.get_vehicle_status(vehicle_number)
        
        if not vehicle_status:
            logger.warning(f"No status found for vehicle {vehicle_number} - cannot capture baseline")
            return False
        
        baseline_data = {
            "baseline_latitude": vehicle_status.get("latitude"),
            "baseline_longitude": vehicle_status.get("longitude"),
            "baseline_gps_time": vehicle_status.get("last_gps_time"),
            "baseline_ignition_state": vehicle_status.get("ignition_state"),
            "baseline_captured_at": time.time(),
            "vehicle_number": vehicle_number
        }
        
        # Store baseline in conversation context
        state_manager.update_context(user_phone, baseline_data)
        
        logger.info(
            "Baseline GPS coordinates captured successfully",
            extra={
                "user_phone": user_phone,
                "vehicle_number": vehicle_number,
                "baseline_latitude": baseline_data["baseline_latitude"],
                "baseline_longitude": baseline_data["baseline_longitude"],
                "baseline_gps_time": baseline_data["baseline_gps_time"]
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(
            f"Error capturing baseline GPS for vehicle {vehicle_number}: {str(e)}",
            extra={"user_phone": user_phone, "vehicle_number": vehicle_number},
            exc_info=True
        )
        return False


def _coordinates_changed(baseline_lat: float, baseline_lng: float, current_lat: float, current_lng: float, threshold: float = 0.0001) -> bool:
    """
    Check if GPS coordinates have meaningfully changed.
    
    Args:
        baseline_lat: Initial latitude
        baseline_lng: Initial longitude
        current_lat: Current latitude
        current_lng: Current longitude
        threshold: Minimum difference to consider as change (default ~11 meters)
        
    Returns:
        True if coordinates changed significantly, False otherwise
    """
    if baseline_lat is None or baseline_lng is None or current_lat is None or current_lng is None:
        return False
    
    lat_diff = abs(current_lat - baseline_lat)
    lng_diff = abs(current_lng - baseline_lng)
    
    changed = lat_diff > threshold or lng_diff > threshold
    
    logger.debug(
        f"Coordinate change analysis: lat_diff={lat_diff:.8f}, lng_diff={lng_diff:.8f}, threshold={threshold}, changed={changed}"
    )
    
    return changed


def _gps_timestamp_updated(baseline_time: str, current_time: str) -> bool:
    """
    Check if GPS timestamp has been updated since baseline.
    
    Args:
        baseline_time: Initial GPS timestamp
        current_time: Current GPS timestamp
        
    Returns:
        True if timestamp updated, False otherwise
    """
    if not baseline_time or not current_time:
        return False
    
    try:
        from datetime import datetime
        
        # Parse timestamps (assuming ISO format)
        if isinstance(baseline_time, str):
            baseline_dt = datetime.fromisoformat(baseline_time.replace('Z', '+00:00'))
        else:
            baseline_dt = baseline_time
            
        if isinstance(current_time, str):
            current_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
        else:
            current_dt = current_time
        
        updated = current_dt > baseline_dt
        
        logger.debug(
            f"GPS timestamp analysis: baseline={baseline_dt}, current={current_dt}, updated={updated}"
        )
        
        return updated
        
    except Exception as e:
        logger.warning(f"Error comparing GPS timestamps: {str(e)}")
        return False


def _perform_gps_verification(user_phone: str, db: Session, state_manager: StateManager) -> str:
    """
    Automatically verify GPS status after repair instructions using baseline comparison.
    Waits 10 seconds, then compares current coordinates with baseline captured earlier.
    
    Args:
        user_phone: User's phone number
        db: Database session
        state_manager: State manager instance for accessing baseline data
        
    Returns:
        Verification result message
    """
    try:
        # Get vehicle number and baseline data from context
        context = state_manager.get_context(user_phone)
        vehicle_number = context.get("vehicle_number") or _get_vehicle_number_for_user(user_phone, db)
        
        if not vehicle_number:
            logger.warning(f"Cannot verify GPS - no vehicle found for user {user_phone}")
            # Clear state on error
            state_manager.clear_state(user_phone)
            return (
                "⚠️ GPS सत्यापन पूरा नहीं हो सका।\n"
                "⚠️ Could not complete GPS verification.\n\n"
                "कृपया मैन्युअल रूप से जांच लें कि GPS काम कर रहा है या नहीं।\n"
                "Please manually check if GPS is working.\n\n"
                "धन्यवाद! / Thank you!"
            )
        
        # Get baseline coordinates from context
        baseline_lat = context.get("baseline_latitude")
        baseline_lng = context.get("baseline_longitude")
        baseline_gps_time = context.get("baseline_gps_time")
        baseline_ignition = context.get("baseline_ignition_state", "").lower()
        
        logger.info(
            f"Starting enhanced GPS verification for user {user_phone}, vehicle {vehicle_number}",
            extra={
                "user_phone": user_phone,
                "vehicle_number": vehicle_number,
                "has_baseline": baseline_lat is not None and baseline_lng is not None,
                "baseline_coords": f"{baseline_lat}, {baseline_lng}" if baseline_lat and baseline_lng else "None",
                "verification_wait_seconds": 10
            }
        )
        
        # Wait 10 seconds for GPS system to stabilize
        logger.info(
            "Waiting 10 seconds for GPS system to stabilize...",
            extra={"user_phone": user_phone, "vehicle_number": vehicle_number}
        )
        time.sleep(10)
        
        logger.info(
            "10-second wait completed, checking current vehicle status",
            extra={"user_phone": user_phone, "vehicle_number": vehicle_number}
        )
        
        # Get current vehicle status using the service
        status_service = VehicleStatusService(db)
        vehicle_status = status_service.get_vehicle_status(vehicle_number)
        
        if not vehicle_status:
            logger.warning(f"No status found for vehicle {vehicle_number}")
            # Clear state on error
            state_manager.clear_state(user_phone)
            return (
                "⚠️ वाहन की स्थिति जांचने में असमर्थ।\n"
                "⚠️ Unable to check vehicle status.\n\n"
                "कृपया मैन्युअल रूप से GPS सिग्नल जांच लें।\n"
                "Please manually check GPS signal.\n\n"
                "धन्यवाद! / Thank you!"
            )
        
        # Get current status
        current_ignition = vehicle_status.get("ignition_state", "").lower()
        current_lat = vehicle_status.get("latitude")
        current_lng = vehicle_status.get("longitude")
        current_gps_time = vehicle_status.get("last_gps_time")
        
        logger.info(
            "GPS verification comparison data",
            extra={
                "user_phone": user_phone,
                "vehicle_number": vehicle_number,
                "baseline_coords": f"{baseline_lat}, {baseline_lng}" if baseline_lat and baseline_lng else "None",
                "current_coords": f"{current_lat}, {current_lng}" if current_lat and current_lng else "None",
                "baseline_ignition": baseline_ignition,
                "current_ignition": current_ignition,
                "baseline_gps_time": baseline_gps_time,
                "current_gps_time": current_gps_time
            }
        )
        
        # Check if ignition is still off
        if current_ignition == "off":
            logger.warning(
                f"Ignition still off after repair attempt for vehicle {vehicle_number}",
                extra={"user_phone": user_phone, "current_ignition": current_ignition}
            )
            # Keep conversation alive for recheck option
            state_manager.set_state(user_phone, ConversationStep.GPS_REPAIR_RECHECK)
            return (
                "⚠️ हम देख सकते हैं कि आपके वाहन का इग्निशन अभी भी बंद है।\n"
                "⚠️ We can see that your vehicle ignition is still off.\n\n"
                "कृपया इग्निशन ऑन करें।\n"
                "Please turn on the ignition.\n\n"
                "इग्निशन ऑन करने के बाद:\n"
                "After turning on the ignition:\n\n"
                "1️⃣ दोबारा चेक करें / Check again\n"
                "2️⃣ बाद में बात करें / Talk later\n\n"
                "धन्यवाद! / Thank you!"
            )
        
        # Check if current GPS coordinates are available
        if current_lat is None or current_lng is None:
            logger.warning(
                f"No current GPS coordinates for vehicle {vehicle_number} after repair",
                extra={
                    "user_phone": user_phone,
                    "vehicle_number": vehicle_number,
                    "current_ignition": current_ignition
                }
            )
            # Keep conversation alive for recheck option
            state_manager.set_state(user_phone, ConversationStep.GPS_REPAIR_RECHECK)
            return (
                "⚠️ इग्निशन ऑन है लेकिन GPS सिग्नल अभी भी नहीं मिल रहा।\n"
                "⚠️ Ignition is on but GPS signal is still not available.\n\n"
                "कृपया:\n"
                "Please:\n\n"
                "• खुली जगह जाएं / Move to an open area\n"
                "• 2-3 मिनट और इंतजार करें / Wait 2-3 more minutes\n\n"
                "तैयार होने पर:\n"
                "When ready:\n\n"
                "1️⃣ दोबारा चेक करें / Check again\n"
                "2️⃣ बाद में बात करें / Talk later\n\n"
                "धन्यवाद! / Thank you!"
            )
        
        # Enhanced verification with baseline comparison
        coordinates_moved = False
        timestamp_updated = False
        
        if baseline_lat is not None and baseline_lng is not None:
            coordinates_moved = _coordinates_changed(baseline_lat, baseline_lng, current_lat, current_lng)
            
        if baseline_gps_time and current_gps_time:
            timestamp_updated = _gps_timestamp_updated(baseline_gps_time, current_gps_time)
        
        logger.info(
            "Enhanced GPS verification results",
            extra={
                "user_phone": user_phone,
                "vehicle_number": vehicle_number,
                "coordinates_moved": coordinates_moved,
                "timestamp_updated": timestamp_updated,
                "gps_verification_method": "baseline_comparison"
            }
        )
        
        # Determine response based on enhanced analysis - ONLY coordinates matter for success
        if coordinates_moved:
            # ONLY case for success: coordinates actually changed - clear state (conversation ends successfully)
            logger.info(
                f"GPS coordinates changed for vehicle {vehicle_number} - repair successful",
                extra={
                    "user_phone": user_phone,
                    "baseline": f"{baseline_lat:.6f}, {baseline_lng:.6f}",
                    "current": f"{current_lat:.6f}, {current_lng:.6f}",
                    "gps_verification": "coordinates_changed_success"
                }
            )
            state_manager.clear_state(user_phone)
            return (
                f"🎉 परफेक्ट! GPS सफलतापूर्वक अपडेट हो रहा है।\n"
                f"🎉 Perfect! GPS is successfully updating.\n\n"
                f"📍 पुराना स्थान: {baseline_lat:.6f}, {baseline_lng:.6f}\n"
                f"📍 Old location: {baseline_lat:.6f}, {baseline_lng:.6f}\n\n"
                f"📍 नया स्थान: {current_lat:.6f}, {current_lng:.6f}\n"
                f"📍 New location: {current_lat:.6f}, {current_lng:.6f}\n\n"
                "निर्देशांक बदलने से पता चलता है कि GPS सिस्टम बिल्कुल सही तरीके से काम कर रहा है! ✅\n"
                "The coordinate change confirms that the GPS system is working perfectly! ✅\n\n"
                "धन्यवाद! / Thank you!"
            )
            
        else:
            # All other cases: keep conversation alive for recheck - coordinates haven't changed
            if timestamp_updated:
                logger.info(
                    f"GPS timestamp updated but coordinates unchanged for vehicle {vehicle_number} - need coordinate change for success",
                    extra={
                        "user_phone": user_phone,
                        "coordinates_same": True,
                        "timestamp_advancing": True,
                        "gps_verification": "timestamp_only_insufficient"
                    }
                )
                # Keep conversation alive for recheck since coordinates haven't changed
                state_manager.set_state(user_phone, ConversationStep.GPS_REPAIR_RECHECK)
                return (
                    f"📍 GPS सिग्नल मिल रहा है लेकिन निर्देशांक नहीं बदले।\n"
                    f"📍 GPS signal is received but coordinates haven't changed.\n\n"
                    f"📍 वर्तमान स्थान: {current_lat:.6f}, {current_lng:.6f}\n"
                    f"📍 Current location: {current_lat:.6f}, {current_lng:.6f}\n\n"
                    "GPS टाइमस्टैम्प अपडेट हो रहा है लेकिन वाहन की स्थिति नहीं बदली है।\n"
                    "GPS timestamp is updating but vehicle position hasn't changed.\n\n"
                    "कृपया:\n"
                    "Please:\n\n"
                    "• वाहन को थोड़ा हिलाएं / Move the vehicle slightly\n"
                    "• खुली जगह जाएं / Move to an open area\n"
                    "• 2-3 मिनट इंतजार करें / Wait 2-3 minutes\n\n"
                    "तैयार होने पर:\n"
                    "When ready:\n\n"
                    "1️⃣ दोबारा चेक करें / Check again\n"
                    "2️⃣ बाद में बात करें / Talk later\n\n"
                    "धन्यवाद! / Thank you!"
                )
            else:
                logger.warning(
                    f"No GPS changes detected for vehicle {vehicle_number} after repair",
                    extra={
                        "user_phone": user_phone,
                        "coordinates_same": True,
                        "timestamp_same": True,
                        "gps_verification": "no_changes_detected"
                    }
                )
                # Keep conversation alive for recheck option
                state_manager.set_state(user_phone, ConversationStep.GPS_REPAIR_RECHECK)
            return (
                f"⚠️ GPS स्थिति में कोई बदलाव नहीं दिखा।\n"
                f"⚠️ No changes detected in GPS status.\n\n"
                f"📍 स्थान: {current_lat:.6f}, {current_lng:.6f}\n"
                f"📍 Location: {current_lat:.6f}, {current_lng:.6f}\n\n"
                "निर्देशांक और टाइमस्टैम्प दोनों अपडेट नहीं हुए हैं।\n"
                "Both coordinates and timestamp haven't updated.\n\n"
                "कृपया:\n"
                "Please:\n\n"
                "• 2-3 मिनट और इंतजार करें / Wait 2-3 more minutes\n"
                "• खुली जगह जाएं / Move to an open area\n"
                "• वाहन को थोड़ा हिलाएं / Move the vehicle slightly\n\n"
                "तैयार होने पर:\n"
                "When ready:\n\n"
                "1️⃣ दोबारा चेक करें / Check again\n"
                "2️⃣ बाद में बात करें / Talk later\n\n"
                "धन्यवाद! / Thank you!"
            )
        
    except Exception as e:
        logger.error(
            f"Error during enhanced GPS verification for user {user_phone}: {str(e)}",
            extra={"user_phone": user_phone},
            exc_info=True
        )
        # Clear state on error
        state_manager.clear_state(user_phone)
        return (
            "⚠️ GPS सत्यापन में त्रुटि हुई।\n"
            "⚠️ Error occurred during GPS verification.\n\n"
            "कृपया मैन्युअल रूप से GPS स्थिति जांच लें।\n"
            "Please manually check GPS status.\n\n"
            "धन्यवाद! / Thank you!"
        )


def _get_company_name_for_user(user_phone: str, db: Session) -> str:
    """
    Get company name for a user based on their associated vehicle.
    
    Args:
        user_phone: User's phone number
        db: Database session
        
    Returns:
        Company name or default company name
    """
    try:
        # First, get the user
        user = db.query(User).filter(User.phone_number == user_phone).first()
        if not user:
            logger.warning(f"User not found for phone: {user_phone}")
            return "Tech Solutions Pvt Ltd"
        
        # Find vehicle associated with this user (as manager, supervisor, or driver)
        vehicle = db.query(Vehicle).filter(
            (Vehicle.manager_id == user.id) |
            (Vehicle.supervisor_id == user.id) |
            (Vehicle.driver_id == user.id)
        ).first()
        
        if vehicle and vehicle.company_name:
            logger.info(f"Found company name '{vehicle.company_name}' for user {user_phone}")
            return vehicle.company_name
        
        # If no vehicle found or no company name, return default
        logger.info(f"No vehicle/company found for user {user_phone}, using default")
        return "Tech Solutions Pvt Ltd"
        
    except Exception as e:
        logger.error(f"Error getting company name for user {user_phone}: {str(e)}")
        return "Tech Solutions Pvt Ltd"


def handle_support_message(user, text_body: str, state_manager: StateManager, db: Session = None) -> str:
    normalized = _normalize_text(text_body)
    greeting_service = GreetingService(state_manager)
    menu_service = MenuService(state_manager, db)

    # Handle greetings - always show welcome menu
    if greeting_service.is_greeting(normalized):
        logger.info(
            "User entered greeting",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)

    # Get current state (state might have been reset in webhook if this is greeting/menu selection)
    state = state_manager.get_state(user.phone_number)
    if state is None:
        logger.info(
            "State not found; initializing MAIN_MENU",
            extra={"phone_number": user.phone_number},
        )
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)

    current_step = state.current_step
    context = state_manager.get_context(user.phone_number)

    # Handle menu selection (1 or 2) - this ensures deterministic behavior
    if current_step == ConversationStep.MAIN_MENU.value:
        # Special case: If user presses "1" and they were contacted as a driver or supervisor for GPS repair
        if normalized == "1" and context.get("contact_type") in ["driver", "supervisor"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_NEAR_VEHICLE)
            logger.info(
                f"{context.get('contact_type', 'contact')} pressed 1 for GPS repair - starting GPS troubleshooting",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value}
            )
            return (
                "हम आपके GPS सिस्टम को ठीक करने में मदद करने के लिए यहाँ हैं। कृपया प्रश्नों के उत्तर दें।\n"
                "We are here to help fix the GPS system. Please answer the questions.\n\n"
                "क्या आप वाहन के पास हैं?\n"
                "Are you near the vehicle?\n\n"
                "1️⃣ हाँ / Yes\n"
                "2️⃣ नहीं / No"
            )
        
        logger.info(
            "Processing menu selection in MAIN_MENU state",
            extra={"phone_number": user.phone_number, "text": text_body}
        )
        return menu_service.handle_menu_selection(user.phone_number, text_body)

    # New unified flow - Ask if user is the manager of specific company
    if current_step == ConversationStep.ASK_RIGHT_PERSON.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CAN_PROVIDE_OTHER_NUMBER)
            logger.info(
                "Right person confirmed - asking for other number",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CAN_PROVIDE_OTHER_NUMBER.value},
            )
            return (
                "बढ़िया! क्या हमें आपके साथ ही जारी रखना चाहिए या किसी और से बात करनी चाहिए?\n"
                "Great! Should we continue with you or should we talk with somebody else?\n\n"
                "1️⃣ मेरे साथ जारी रखें / Continue with me\n"
                "2️⃣ किसी और से बात करें / Talk with someone else"
            )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_NUMBER)
            logger.info(
                "Wrong person - asking for contact",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CONTACT_NUMBER.value},
            )
            return (
                "कोई बात नहीं। कृपया सही व्यक्ति का फोन नंबर दें जिससे हमें बात करनी चाहिए।\n"
                "No problem. Please provide the phone number of the right person we should talk to.\n\n"
                "उदाहरण / Example: 9876543210"
            )

        logger.warning(
            "Invalid right person response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        
        # Get company name for this user and show the proper message
        company_name = _get_company_name_for_user(user.phone_number, db) if db else "Tech Solutions Pvt Ltd"
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            f"क्या हम {company_name} के मैनेजर/सुपरवाइजर से बात कर रहे हैं?\n"
            f"Are we talking to the manager/supervisor of {company_name}?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )

    # Handle if manager can provide other number
    if current_step == ConversationStep.ASK_CAN_PROVIDE_OTHER_NUMBER.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa", "continue", "मेरे साथ"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_NEAR_VEHICLE)
            logger.info(
                "Manager wants to continue with themselves - starting GPS repair flow",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value},
            )
            return (
                "हम आपके GPS सिस्टम को ठीक करने में मदद करने के लिए यहाँ हैं। कृपया प्रश्नों के उत्तर दें।\n"
                "We are here to help fix the GPS system. Please answer the questions.\n\n"
                "क्या आप वाहन के पास हैं?\n"
                "Are you near the vehicle?\n\n"
                "1️⃣ हाँ / Yes\n"
                "2️⃣ नहीं / No"
            )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin", "someone else", "किसी और"]:
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_TYPE)
            logger.info(
                "Manager wants to talk with someone else - asking contact type with driver info",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CONTACT_TYPE.value},
            )
            
            # Get driver number from database for this user's vehicle
            driver_number = "Not available"
            if db:
                try:
                    # First, get the user
                    manager = db.query(User).filter(User.phone_number == user.phone_number).first()
                    if manager:
                        # Find vehicle where this user is manager
                        vehicle = db.query(Vehicle).filter(Vehicle.manager_id == manager.id).first()
                        if vehicle and vehicle.driver_id:
                            # Get driver details
                            driver = db.query(User).filter(User.id == vehicle.driver_id).first()
                            if driver and driver.phone_number:
                                driver_number = driver.phone_number
                                logger.info(f"Found driver number {driver_number} for manager {user.phone_number}")
                except Exception as e:
                    logger.error(f"Error fetching driver number: {str(e)}")
            
            return (
                "क्या हमें सुपरवाइजर या ड्राइवर से संपर्क करना चाहिए?\n"
                "Should we contact supervisor or driver?\n\n"
                "1️⃣ सुपरवाइजर / Supervisor\n"
                f"2️⃣ ड्राइवर / Driver whose number is {driver_number}"
            )

        logger.warning(
            "Invalid continue or someone else response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या हमें आपके साथ ही जारी रखना चाहिए या किसी और से बात करनी चाहिए?\n"
            "Should we continue with you or should we talk with somebody else?\n\n"
            "1️⃣ मेरे साथ जारी रखें / Continue with me\n"
            "2️⃣ किसी और से बात करें / Talk with someone else"
        )

    # Handle contact type selection
    if current_step == ConversationStep.ASK_CONTACT_TYPE.value:
        if normalized in ["1", "supervisor", "सुपरवाइजर"]:
            state_manager.update_context(user.phone_number, {"contact_type": "supervisor"})
            state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_NUMBER)
            logger.info(
                "Contact type selected: supervisor",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_CONTACT_NUMBER.value},
            )
            return (
                "सुपरवाइजर का फोन नंबर दें।\n"
                "Please provide supervisor's phone number.\n\n"
                "उदाहरण / Example: 9876543210"
            )

        if normalized in ["2", "driver", "ड्राइवर"]:
            # Use driver number from database
            driver_number = None
            if db:
                try:
                    # Get the manager user
                    manager = db.query(User).filter(User.phone_number == user.phone_number).first()
                    if manager:
                        # Find vehicle where this user is manager
                        vehicle = db.query(Vehicle).filter(Vehicle.manager_id == manager.id).first()
                        if vehicle and vehicle.driver_id:
                            # Get driver details
                            driver = db.query(User).filter(User.id == vehicle.driver_id).first()
                            if driver and driver.phone_number:
                                driver_number = driver.phone_number
                                logger.info(f"Using driver number {driver_number} from database")
                except Exception as e:
                    logger.error(f"Error fetching driver number for contact: {str(e)}")
            
            if driver_number:
                # Directly proceed to send message to driver using database number
                state_manager.update_context(user.phone_number, {
                    "contact_type": "driver",
                    "contact_number": driver_number,
                    "original_contact_input": driver_number
                })
                
                # Create driver message
                breakdown_message = (
                    "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                    "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                    "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                    "आप ड्राइवर हैं। कृपया सहायता के लिए 1 दबाएं।\n"
                    "You are the driver. Please press 1 for assistance.\n\n"
                    "1️⃣ Press 1 for AI assistance"
                )
                
                # Send message to driver
                success, error_message = _send_whatsapp_with_detailed_logging(
                    driver_number, 
                    breakdown_message,
                    context={
                        "original_user": user.phone_number,
                        "contact_type": "driver",
                        "original_input": "database_driver"
                    }
                )
                
                if success:
                    # Pre-create conversation state for the driver
                    contact_state_manager = StateManager(db) if db else state_manager
                    contact_state_manager.set_state(
                        driver_number,
                        ConversationStep.MAIN_MENU,
                        context_json={"contact_type": "driver", "alert_received": True}
                    )
                    
                    # Clear original user's conversation state
                    state_manager.clear_state(user.phone_number)
                    logger.info(
                        "Driver alert sent successfully using database number",
                        extra={
                            "original_phone": user.phone_number,
                            "driver_phone": driver_number
                        }
                    )
                    
                    return (
                        f"✅ सफलतापूर्वक संदेश भेजा गया!\n"
                        f"✅ Message sent successfully!\n\n"
                        f"📱 संदेश भेजा गया (ड्राइवर / Driver): {driver_number}\n"
                        f"📱 Message sent to (Driver): {driver_number}\n\n"
                        "उन्हें बताया गया है कि GPS में समस्या है और सहायता की जरूरत है।\n"
                        "They have been informed that there are GPS issues and assistance is needed.\n\n"
                        "वे जल्दी ही हमसे संपर्क करेंगे।\n"
                        "They will contact us soon for support."
                    )
                else:
                    logger.error(
                        "Failed to send driver alert using database number",
                        extra={
                            "original_phone": user.phone_number,
                            "driver_phone": driver_number,
                            "error": error_message
                        }
                    )
                    return (
                        f"❌ ड्राइवर को संदेश भेजने में त्रुटि: {error_message}\n"
                        f"❌ Error sending message to driver: {error_message}\n\n"
                        f"ड्राइवर का नंबर: {driver_number}\n"
                        f"Driver's number: {driver_number}\n\n"
                        "कृपया बाद में कोशिश करें।\n"
                        "Please try again later."
                    )
            else:
                # No driver number found, ask for manual input
                state_manager.update_context(user.phone_number, {"contact_type": "driver"})
                state_manager.set_state(user.phone_number, ConversationStep.ASK_CONTACT_NUMBER)
                logger.warning(
                    "No driver number found in database, asking for manual input",
                    extra={"phone_number": user.phone_number}
                )
                return (
                    "ड्राइवर का नंबर डेटाबेस में नहीं मिला। कृपया ड्राइवर का फोन नंबर दें।\n"
                    "Driver number not found in database. Please provide driver's phone number.\n\n"
                    "उदाहरण / Example: 9876543210"
                )

        logger.warning(
            "Invalid contact type response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        
        # Get driver number again for error message
        driver_number = "Not available"
        if db:
            try:
                manager = db.query(User).filter(User.phone_number == user.phone_number).first()
                if manager:
                    vehicle = db.query(Vehicle).filter(Vehicle.manager_id == manager.id).first()
                    if vehicle and vehicle.driver_id:
                        driver = db.query(User).filter(User.id == vehicle.driver_id).first()
                        if driver and driver.phone_number:
                            driver_number = driver.phone_number
            except Exception as e:
                logger.error(f"Error fetching driver number for error message: {str(e)}")
        
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या हमें सुपरवाइजर या ड्राइवर से संपर्क करना चाहिए?\n"
            "Should we contact supervisor or driver?\n\n"
            "1️⃣ सुपरवाइजर / Supervisor\n"
            f"2️⃣ ड्राइवर / Driver whose number is {driver_number}"
        )

    # Handle problem description
    if current_step == ConversationStep.ASK_PROBLEM_DESCRIPTION.value:
        state_manager.update_context(user.phone_number, {"problem_description": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.VEHICLE_NUMBER)
        logger.info(
            "Problem description received",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.VEHICLE_NUMBER.value},
        )
        return (
            "धन्यवाद। अब कृपया वाहन का नंबर बताएं।\n"
            "Thank you. Now please provide the vehicle number.\n\n"
            "उदाहरण / Example: DL01AB1234"
        )

    # Handle contact number for wrong person scenario OR for supervisor/driver
    if current_step == ConversationStep.ASK_CONTACT_NUMBER.value:
        contact_input = text_body.strip()
        context = state_manager.get_context(user.phone_number)
        contact_type = context.get("contact_type", "manager")  # Default to manager for backward compatibility
        
        logger.info(
            "Processing contact number input",
            extra={
                "original_phone": user.phone_number,
                "contact_input": contact_input,
                "contact_type": contact_type
            }
        )
        
        # Validate and normalize phone number
        normalized_contact, validation_error = _normalize_phone_number(contact_input)
        
        if validation_error:
            logger.warning(
                "Invalid contact number provided",
                extra={
                    "original_phone": user.phone_number,
                    "contact_input": contact_input,
                    "validation_error": validation_error,
                    "contact_type": contact_type
                }
            )
            return (
                f"❌ फोन नंबर सही नहीं है: {validation_error}\n"
                f"❌ Phone number is incorrect: {validation_error}\n\n"
                "कृपया सही फोन नंबर दें। उदाहरण:\n"
                "Please provide a correct phone number. Examples:\n"
                "• 9876543210\n"
                "• +919876543210\n"
                "• 919876543210"
            )
        
        # Store the contact information
        state_manager.update_context(user.phone_number, {
            "contact_number": normalized_contact,
            "original_contact_input": contact_input,
            "contact_type": contact_type
        })
        
        # Create appropriate message based on contact type
        if contact_type == "supervisor":
            breakdown_message = (
                "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                "आप सुपरवाइजर हैं। कृपया सहायता के लिए 1 दबाएं।\n"
                "You are the supervisor. Please press 1 for assistance.\n\n"
                "1️⃣ Press 1 for AI assistance"
            )
        elif contact_type == "driver":
            breakdown_message = (
                "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                "आप ड्राइवर हैं। कृपया सहायता के लिए 1 दबाएं।\n"
                "You are the driver. Please press 1 for assistance.\n\n"
                "1️⃣ Press 1 for AI assistance"
            )
        else:
            # Default message for manager/other contacts (backward compatibility)
            breakdown_message = (
                "🚨 वाहन सहायता अलर्ट / Vehicle Support Alert\n\n"
                "वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।\n"
                "Vehicle has technical issues - GPS is not working and data transmission has stopped.\n\n"
                "हम आपकी सहायता के लिए यहाँ हैं।\n"
                "We are here to help you.\n\n"
                "1️⃣ Press 1 for AI assistance"
            )
        
        # Send breakdown notification with enhanced error handling
        success, error_message = _send_whatsapp_with_detailed_logging(
            normalized_contact, 
            breakdown_message,
            context={
                "original_user": user.phone_number,
                "contact_type": contact_type,
                "original_input": contact_input
            }
        )
        
        if success:
            # Pre-create conversation state for the contact person with appropriate context
            contact_state_manager = StateManager(db) if db else state_manager
            contact_state_manager.set_state(
                normalized_contact,
                ConversationStep.MAIN_MENU,
                context_json={"contact_type": contact_type, "alert_received": True}
            )
            
            # Clear original user's conversation state after successful message
            state_manager.clear_state(user.phone_number)
            logger.info(
                "Breakdown alert successfully sent to contact person with pre-created state",
                extra={
                    "original_phone": user.phone_number,
                    "contact_phone": normalized_contact,
                    "contact_type": contact_type,
                    "original_input": contact_input
                }
            )
            
            contact_type_display = {
                "supervisor": "सुपरवाइजर / Supervisor",
                "driver": "ड्राइवर / Driver", 
                "manager": "मैनेजर / Manager"
            }.get(contact_type, contact_type)
            
            return (
                f"✅ सफलतापूर्वक संदेश भेजा गया!\n"
                f"✅ Message sent successfully!\n\n"
                f"📱 संदेश भेजा गया ({contact_type_display}): {normalized_contact}\n"
                f"📱 Message sent to ({contact_type_display}): {normalized_contact}\n\n"
                "उन्हें बताया गया है कि मशीन टूटी हुई है और सहायता की जरूरत है।\n"
                "They have been informed that the machine is broken and needs assistance.\n\n"
                "वे जल्दी ही हमसे संपर्क करेंगे।\n"
                "They will contact us soon for support."
            )
        else:
            logger.error(
                "Failed to send breakdown alert to contact person",
                extra={
                    "original_phone": user.phone_number,
                    "contact_phone": normalized_contact,
                    "contact_type": contact_type,
                    "error": error_message,
                    "original_input": contact_input
                }
            )
            
            # Don't clear state on failure - let user try again
            return (
                f"❌ संदेश भेजने में त्रुटि: {error_message}\n"
                f"❌ Error sending message: {error_message}\n\n"
                "कृपया फिर से कोशिश करें या दूसरा नंबर दें।\n"
                "Please try again or provide a different number.\n\n"
                f"आपका दिया गया नंबर: {normalized_contact}\n"
                f"Number you provided: {normalized_contact}"
            )

    # GPS Repair Flow - Ask if driver is near vehicle
    if current_step == ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa"]:
            # Capture baseline GPS coordinates before starting repair
            vehicle_number = _get_vehicle_number_for_user(user.phone_number, db)
            if vehicle_number and db:
                baseline_captured = _capture_baseline_gps_coordinates(
                    user.phone_number, 
                    vehicle_number, 
                    db, 
                    state_manager
                )
                logger.info(
                    f"Baseline GPS capture result for repair process: {baseline_captured}",
                    extra={
                        "phone_number": user.phone_number,
                        "vehicle_number": vehicle_number,
                        "baseline_captured": baseline_captured
                    }
                )
            
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CHECK_IGNITION)
            logger.info(
                "Driver is near vehicle - baseline captured, will check ignition status automatically",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_CHECK_IGNITION.value},
            )
            
            try:
                # Send initial waiting message
                initial_message = (
                    "बहुत अच्छा! अब हमें आपके वाहन की इग्निशन स्थिति की जांच करनी होगी।\n"
                    "Great! Now we need to check your vehicle's ignition status.\n\n"
                    "कृपया 2-3 सेकंड प्रतीक्षा करें जबकि हम जांच करते हैं।\n"
                    "Please wait 2-3 seconds while we check."
                )
                send_whatsapp_message(user.phone_number, initial_message)
                
                # Automatically check ignition after 3 seconds
                import time
                import threading
                def check_ignition_automatically():
                    time.sleep(3)
                    
                    try:
                        from app.services.vehicle_status_service import VehicleStatusService
                        status_service = VehicleStatusService(db)
                        vehicle_status = status_service.get_vehicle_status(vehicle_number)
                        
                        if not vehicle_status:
                            logger.warning(f"No vehicle status available for automatic ignition check - {vehicle_number}")
                            fallback_message = (
                                "वाहन की स्थिति की जांच नहीं हो सकी। चलिए सामान्य प्रक्रिया से आगे बढ़ते हैं।\n"
                                "Could not check vehicle status. Let's proceed with normal process.\n\n"
                                "पहले वाहन का कट आउट बंद करें।\n"
                                "First turn off the vehicle cut out.\n\n"
                                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                                "Press '1' after turning off the cut out.\n\n"
                                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                                "2️⃣ कट आउट नहीं मिला / Cut out not found"
                            )
                            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                            send_whatsapp_message(user.phone_number, fallback_message)
                            return
                        
                        current_ignition = vehicle_status.get("ignition_state", "").lower()
                        logger.info(
                            f"Automatic ignition status check for vehicle {vehicle_number}: {current_ignition}",
                            extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number, "ignition_state": current_ignition}
                        )
                        
                        if current_ignition == "on":
                            # Ignition is on - ask if driver is driving
                            state_manager.update_context(user.phone_number, {"ignition_was_on": True})
                            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                            ignition_on_message = (
                                "हमने देखा कि आपके वाहन की इग्निशन चालू है।\n"
                                "We can see that your vehicle ignition is on.\n\n"
                                "क्या आप अभी गाड़ी चला रहे हैं?\n"
                                "Are you currently driving?\n\n"
                                "अगर हां, तो क्या आप कुछ मिनटों के लिए वाहन को सुरक्षित जगह पार्क कर सकते हैं? GPS की मरम्मत के लिए इग्निशन बंद करना होगा।\n"
                                "If yes, can you park the vehicle safely for a few minutes? We need to turn off ignition for GPS repair.\n\n"
                                "1️⃣ मैं वाहन पार्क कर दूंगा / I'll park the vehicle\n"
                                "2️⃣ मैं ड्राइविंग नहीं कर रहा / I'm not driving"
                            )
                            send_whatsapp_message(user.phone_number, ignition_on_message)
                        else:
                            # Ignition is off - continue with cut out step
                            state_manager.update_context(user.phone_number, {"ignition_was_on": False})
                            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                            ignition_off_message = (
                                "बढ़िया! आपके वाहन की इग्निशन बंद है। अब हम GPS की मरम्मत शुरू कर सकते हैं।\n"
                                "Great! Your vehicle ignition is off. Now we can start GPS repair.\n\n"
                                "पहले वाहन का कट आउट बंद करें।\n"
                                "First turn off the vehicle cut out.\n\n"
                                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                                "Press '1' after turning off the cut out.\n\n"
                                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                                "2️⃣ कट आउट नहीं मिला / Cut out not found"
                            )
                            send_whatsapp_message(user.phone_number, ignition_off_message)
                            
                    except Exception as e:
                        logger.error(f"Error in automatic ignition check: {str(e)}", exc_info=True)
                        # Fallback to manual flow
                        fallback_message = (
                            "इग्निशन स्थिति की जांच में समस्या हुई। चलिए सामान्य प्रक्रिया से आगे बढ़ते हैं।\n"
                            "There was an issue checking ignition status. Let's proceed with normal process.\n\n"
                            "पहले वाहन का कट आउट बंद करें।\n"
                            "First turn off the vehicle cut out.\n\n"
                            "कट आउट बंद करने के बाद '1' दबाएं।\n"
                            "Press '1' after turning off the cut out.\n\n"
                            "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                            "2️⃣ कट आउट नहीं मिला / Cut out not found"
                        )
                        state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                        send_whatsapp_message(user.phone_number, fallback_message)
                
                # Start automatic ignition check in background
                thread = threading.Thread(target=check_ignition_automatically)
                thread.daemon = True
                thread.start()
                
                return initial_message
                
            except Exception as e:
                logger.error(f"Failed to start automatic ignition check: {str(e)}")
                # Fallback to manual flow
                state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                return (
                    "इग्निशन जांच शुरू नहीं हो सकी। सामान्य प्रक्रिया से आगे बढ़ते हैं।\n"
                    "Could not start ignition check. Proceeding with normal process.\n\n"
                    "पहले वाहन का कट आउट बंद करें।\n"
                    "First turn off the vehicle cut out.\n\n"
                    "कट आउट बंद करने के बाद '1' दबाएं।\n"
                    "Press '1' after turning off the cut out.\n\n"
                    "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                    "2️⃣ कट आउट नहीं मिला / Cut out not found"
                )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_TIME_ESTIMATE)
            logger.info(
                "Driver is not near vehicle - asking for time estimate to reach vehicle",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_TIME_ESTIMATE.value},
            )
            return (
                "कोई बात नहीं। आप लगभग कितने समय में वाहन के पास पहुंच सकते हैं?\n"
                "No problem. Approximately how much time will it take you to reach the vehicle?\n\n"
                "1️⃣ 10 सेकंड / 10 seconds\n"
                "2️⃣ 20 सेकंड / 20 seconds\n"
                "3️⃣ 30 सेकंड / 30 seconds\n"
                "4️⃣ मैं वाहन के पास हूं / I am near the vehicle"
            )

        logger.warning(
            "Invalid near vehicle response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या आप वाहन के पास हैं?\n"
            "Are you near the vehicle?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )

    # GPS Repair Flow - Handle time estimate for reaching vehicle
    if current_step == ConversationStep.GPS_REPAIR_TIME_ESTIMATE.value:
        if normalized in ["1", "10", "10 sec", "10 seconds"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_WAITING_FOR_DRIVER)
            state_manager.update_context(user.phone_number, {"wait_time": 10})
            logger.info(
                "Driver selected 10 seconds - will follow up after waiting",
                extra={"phone_number": user.phone_number, "wait_time": 10}
            )
            
            # Send immediate response and schedule follow-up after 10 seconds
            try:
                # Send immediate response
                initial_message = (
                    "ठीक है। हम 10 सेकंड प्रतीक्षा करेंगे और फिर आपसे पूछेंगे।\n"
                    "Alright. We will wait 10 seconds and then ask you.\n\n"
                    "कृपया वाहन के पास जाएं।\n"
                    "Please go near the vehicle."
                )
                send_whatsapp_message(user.phone_number, initial_message)
                
                # Wait 10 seconds and send follow-up
                import time
                import threading
                def send_followup():
                    time.sleep(10)
                    followup_message = (
                        "क्या आप अब वाहन के पास हैं?\n"
                        "Are you now near the vehicle?\n\n"
                        "1️⃣ हाँ / Yes\n"
                        "2️⃣ नहीं / No"
                    )
                    try:
                        send_whatsapp_message(user.phone_number, followup_message)
                    except Exception as e:
                        logger.error(f"Failed to send follow-up message: {str(e)}")
                
                # Start the delay in background
                thread = threading.Thread(target=send_followup)
                thread.daemon = True
                thread.start()
                
                return initial_message
                
            except Exception as e:
                logger.error(f"Failed to send time estimate message: {str(e)}")
                return (
                    "ठीक है। 10 सेकंड बाद हम आपसे पूछेंगे कि क्या आप वाहन के पास हैं।\n"
                    "Alright. After 10 seconds we will ask if you are near the vehicle."
                )
            
        if normalized in ["2", "20", "20 sec", "20 seconds"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_WAITING_FOR_DRIVER)
            state_manager.update_context(user.phone_number, {"wait_time": 20})
            logger.info(
                "Driver selected 20 seconds - will follow up after waiting",
                extra={"phone_number": user.phone_number, "wait_time": 20}
            )
            
            try:
                # Send immediate response
                initial_message = (
                    "ठीक है। हम 20 सेकंड प्रतीक्षा करेंगे और फिर आपसे पूछेंगे।\n"
                    "Alright. We will wait 20 seconds and then ask you.\n\n"
                    "कृपया वाहन के पास जाएं।\n"
                    "Please go near the vehicle."
                )
                send_whatsapp_message(user.phone_number, initial_message)
                
                # Wait 20 seconds and send follow-up
                import time
                import threading
                def send_followup():
                    time.sleep(20)
                    followup_message = (
                        "क्या आप अब वाहन के पास हैं?\n"
                        "Are you now near the vehicle?\n\n"
                        "1️⃣ हाँ / Yes\n"
                        "2️⃣ नहीं / No"
                    )
                    try:
                        send_whatsapp_message(user.phone_number, followup_message)
                    except Exception as e:
                        logger.error(f"Failed to send follow-up message: {str(e)}")
                
                thread = threading.Thread(target=send_followup)
                thread.daemon = True
                thread.start()
                
                return initial_message
                
            except Exception as e:
                logger.error(f"Failed to send time estimate message: {str(e)}")
                return (
                    "ठीक है। 20 सेकंड बाद हम आपसे पूछेंगे कि क्या आप वाहन के पास हैं।\n"
                    "Alright. After 20 seconds we will ask if you are near the vehicle."
                )
            
        if normalized in ["3", "30", "30 sec", "30 seconds"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_WAITING_FOR_DRIVER)
            state_manager.update_context(user.phone_number, {"wait_time": 30})
            logger.info(
                "Driver selected 30 seconds - will follow up after waiting",
                extra={"phone_number": user.phone_number, "wait_time": 30}
            )
            
            try:
                # Send immediate response
                initial_message = (
                    "ठीक है। हम 30 सेकंड प्रतीक्षा करेंगे और फिर आपसे पूछेंगे।\n"
                    "Alright. We will wait 30 seconds and then ask you.\n\n"
                    "कृपया वाहन के पास जाएं।\n"
                    "Please go near the vehicle."
                )
                send_whatsapp_message(user.phone_number, initial_message)
                
                # Wait 30 seconds and send follow-up
                import time
                import threading
                def send_followup():
                    time.sleep(30)
                    followup_message = (
                        "क्या आप अब वाहन के पास हैं?\n"
                        "Are you now near the vehicle?\n\n"
                        "1️⃣ हाँ / Yes\n"
                        "2️⃣ नहीं / No"
                    )
                    try:
                        send_whatsapp_message(user.phone_number, followup_message)
                    except Exception as e:
                        logger.error(f"Failed to send follow-up message: {str(e)}")
                
                thread = threading.Thread(target=send_followup)
                thread.daemon = True
                thread.start()
                
                return initial_message
                
            except Exception as e:
                logger.error(f"Failed to send time estimate message: {str(e)}")
                return (
                    "ठीक है। 30 सेकंड बाद हम आपसे पूछेंगे कि क्या आप वाहन के पास हैं।\n"
                    "Alright. After 30 seconds we will ask if you are near the vehicle."
                )
            
        if normalized in ["4", "near", "वाहन के पास", "पास", "vehicle"]:
            # Driver is already near vehicle - capture baseline and proceed to cut out step (original flow)
            vehicle_number = _get_vehicle_number_for_user(user.phone_number, db)
            if vehicle_number and db:
                baseline_captured = _capture_baseline_gps_coordinates(
                    user.phone_number, 
                    vehicle_number, 
                    db, 
                    state_manager
                )
                logger.info(
                    f"Driver already near vehicle - baseline captured: {baseline_captured}",
                    extra={
                        "phone_number": user.phone_number,
                        "vehicle_number": vehicle_number,
                        "baseline_captured": baseline_captured
                    }
                )
            
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
            logger.info(
                "Driver confirmed already near vehicle - proceeding to cut out step",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_CUT_OUT.value}
            )
            return (
                "बहुत अच्छा! पहले वाहन का कट आउट बंद करें।\n"
                "Great! First turn off the vehicle cut out.\n\n"
                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off the cut out.\n\n"
                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )
        
        # Invalid response handling
        logger.warning(
            "Invalid time estimate response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "आप लगभग कितने समय में वाहन के पास पहुंच सकते हैं?\n"
            "Approximately how much time will it take you to reach the vehicle?\n\n"
            "1️⃣ 10 सेकंड / 10 seconds\n"
            "2️⃣ 20 सेकंड / 20 seconds\n"
            "3️⃣ 30 सेकंड / 30 seconds\n"
            "4️⃣ मैं वाहन के पास हूं / I am near the vehicle"
        )

    # GPS Repair Flow - Handle responses after waiting for driver to reach vehicle  
    if current_step == ConversationStep.GPS_REPAIR_WAITING_FOR_DRIVER.value:
        if _is_affirmative(normalized) or normalized in ["1", "haan", "yes", "haa"]:
            # Driver confirmed they're now near vehicle - capture baseline and proceed to cut out step (original flow)
            vehicle_number = _get_vehicle_number_for_user(user.phone_number, db)
            if vehicle_number and db:
                baseline_captured = _capture_baseline_gps_coordinates(
                    user.phone_number, 
                    vehicle_number, 
                    db, 
                    state_manager
                )
                logger.info(
                    f"Driver reached vehicle after waiting - baseline captured: {baseline_captured}",
                    extra={
                        "phone_number": user.phone_number,
                        "vehicle_number": vehicle_number,
                        "baseline_captured": baseline_captured
                    }
                )
            
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
            logger.info(
                "Driver reached vehicle after waiting - proceeding to cut out step",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_CUT_OUT.value}
            )
            return (
                "बहुत अच्छा! पहले वाहन का कट आउट बंद करें।\n"
                "Great! First turn off the vehicle cut out.\n\n"
                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off the cut out.\n\n"
                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )

        if _is_negative(normalized) or normalized in ["2", "nahi", "no", "nahin"]:
            # Driver still not near - go back to scheduling callback or give more time
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_SCHEDULE_CALLBACK)
            logger.info(
                "Driver still not near vehicle after waiting - asking for callback schedule",
                extra={"phone_number": user.phone_number}
            )
            return (
                "कोई बात नहीं। क्या आप वाहन के पास जा सकते हैं या हमें बताएं कि हमें आपको कब वापस कॉल करना चाहिए?\n"
                "No problem. Can you go to the vehicle or tell us when we should call you back?\n\n"
                "1️⃣ मैं वाहन के पास जा सकता हूं / I can go to the vehicle\n"
                "2️⃣ बाद में कॉल करें / Call back later"
            )

        # Invalid response
        logger.warning(
            "Invalid response while waiting for driver to reach vehicle",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "क्या आप अब वाहन के पास हैं?\n"
            "Are you now near the vehicle?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        )

    # GPS Repair Flow - Check ignition status and handle driving scenario
    # NOTE: This handler is disabled because we now use automatic ignition checking
    # via threading in GPS_REPAIR_NEAR_VEHICLE handler to prevent duplicate messages
    if False and current_step == ConversationStep.GPS_REPAIR_CHECK_IGNITION.value:
        # Get vehicle status to check ignition
        vehicle_number = _get_vehicle_number_for_user(user.phone_number, db)
        if not vehicle_number:
            logger.warning(f"Cannot check ignition - no vehicle found for user {user.phone_number}")
            # Continue with normal flow if can't get vehicle status
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
            return (
                "वाहन की स्थिति प्राप्त नहीं हो सकी। चलिए सामान्य प्रक्रिया से आगे बढ़ते हैं।\n"
                "Could not get vehicle status. Let's proceed with normal process.\n\n"
                "पहले वाहन का कट आउट बंद करें।\n"
                "First turn off the vehicle cut out.\n\n"
                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off the cut out.\n\n"
                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )

        try:
            from app.services.vehicle_status_service import VehicleStatusService
            status_service = VehicleStatusService(db)
            vehicle_status = status_service.get_vehicle_status(vehicle_number)
            
            if not vehicle_status:
                logger.warning(f"No vehicle status available for {vehicle_number}")
                # Continue with normal flow if can't get status
                state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                return (
                    "वाहन की स्थिति की जांच नहीं हो सकी। चलिए सामान्य प्रक्रिया से आगे बढ़ते हैं।\n"
                    "Could not check vehicle status. Let's proceed with normal process.\n\n"
                    "पहले वाहन का कट आउट बंद करें।\n"
                    "First turn off the vehicle cut out.\n\n"
                    "कट आउट बंद करने के बाद '1' दबाएं।\n"
                    "Press '1' after turning off the cut out.\n\n"
                    "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                    "2️⃣ कट आउट नहीं मिला / Cut out not found"
                )
            
            current_ignition = vehicle_status.get("ignition_state", "").lower()
            logger.info(
                f"Ignition status check for vehicle {vehicle_number}: {current_ignition}",
                extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number, "ignition_state": current_ignition}
            )
            
            if current_ignition == "on":
                # Ignition is on - ask if driver is driving and can park
                state_manager.update_context(user.phone_number, {"ignition_was_on": True})
                state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                logger.info(
                    "Ignition is ON - asking driver if they are driving and can park",
                    extra={"phone_number": user.phone_number, "ignition_state": current_ignition}
                )
                return (
                    "हमने देखा कि आपके वाहन की इग्निशन चालू है।\n"
                    "We can see that your vehicle ignition is on.\n\n"
                    "क्या आप अभी गाड़ी चला रहे हैं?\n"
                    "Are you currently driving?\n\n"
                    "अगर हां, तो क्या आप कुछ मिनटों के लिए वाहन को सुरक्षित जगह पार्क कर सकते हैं? GPS की मरम्मत के लिए इग्निशन बंद करना होगा।\n"
                    "If yes, can you park the vehicle safely for a few minutes? We need to turn off ignition for GPS repair.\n\n"
                    "1️⃣ मैं वाहन पार्क कर दूंगा / I'll park the vehicle\n"
                    "2️⃣ मैं ड्राइविंग नहीं कर रहा / I'm not driving"
                )
            else:
                # Ignition is off - continue with normal flow
                state_manager.update_context(user.phone_number, {"ignition_was_on": False})
                state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
                logger.info(
                    "Ignition is OFF - proceeding with normal GPS repair flow",
                    extra={"phone_number": user.phone_number, "ignition_state": current_ignition}
                )
                return (
                    "बढ़िया! आपके वाहन की इग्निशन बंद है। अब हम GPS की मरम्मत शुरू कर सकते हैं।\n"
                    "Great! Your vehicle ignition is off. Now we can start GPS repair.\n\n"
                    "पहले वाहन का कट आउट बंद करें।\n"
                    "First turn off the vehicle cut out.\n\n"
                    "कट आउट बंद करने के बाद '1' दबाएं।\n"
                    "Press '1' after turning off the cut out.\n\n"
                    "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                    "2️⃣ कट आउट नहीं मिला / Cut out not found"
                )
                
        except Exception as e:
            logger.error(
                f"Error checking ignition status for user {user.phone_number}: {str(e)}",
                extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number},
                exc_info=True
            )
            # Continue with normal flow on error
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
            return (
                "इग्निशन स्थिति की जांच में समस्या हुई। चलिए सामान्य प्रक्रिया से आगे बढ़ते हैं।\n"
                "There was an issue checking ignition status. Let's proceed with normal process.\n\n"
                "पहले वाहन का कट आउट बंद करें।\n"
                "First turn off the vehicle cut out.\n\n"
                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off the cut out.\n\n"
                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )

    # GPS Repair Flow - Handle cut out confirmation or driving scenario
    if current_step == ConversationStep.GPS_REPAIR_CUT_OUT.value:
        context = state_manager.get_context(user.phone_number)
        ignition_was_on = context.get("ignition_was_on", False)
        parking_instructions_given = context.get("parking_instructions_given", False)
        
        # Handle driving scenario responses (when ignition was on)
        if ignition_was_on and not parking_instructions_given and normalized in ["1", "park", "पार्क"]:
            logger.info(
                "Driver will park the vehicle - giving parking instructions",
                extra={"phone_number": user.phone_number, "driving_scenario": True}
            )
            # Set flag to track that parking instructions have been given
            state_manager.update_context(user.phone_number, {"parking_instructions_given": True})
            return (
                "बहुत अच्छा! कृपया वाहन को सुरक्षित जगह पार्क करें।\n"
                "Very good! Please park the vehicle in a safe place.\n\n"
                "पार्क करने के बाद इग्निशन बंद करें और फिर कट आउट बंद करें।\n"
                "After parking, turn off the ignition and then turn off the cut out.\n\n"
                "दोनों बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off both.\n\n"
                "1️⃣ इग्निशन और कट आउट दोनों बंद कर दिया / Both ignition and cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )
            
        if ignition_was_on and not parking_instructions_given and normalized in ["2", "not driving", "नहीं"]:
            logger.info(
                "Driver was not driving - giving instructions to turn off ignition and cut out",
                extra={"phone_number": user.phone_number, "driving_scenario": True}
            )
            # Set flag to track that instructions have been given
            state_manager.update_context(user.phone_number, {"parking_instructions_given": True})
            return (
                "ठीक है! तो कृपया पहले इग्निशन बंद करें और फिर कट आउट बंद करें।\n"
                "Alright! Then please first turn off the ignition and then turn off the cut out.\n\n"
                "दोनों बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off both.\n\n"
                "1️⃣ इग्निशन और कट आउट दोनों बंद कर दिया / Both ignition and cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )
        
        # Handle completion responses after parking instructions were given (or normal flow)
        if normalized in ["1", "done", "cut out off", "ok", "बंद"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_IGNITION)
            # Clear the parking instruction flag as we're moving to next step
            state_manager.update_context(user.phone_number, {"parking_instructions_given": False})
            logger.info(
                "Cut out turned off successfully - asking to turn on ignition",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_IGNITION.value, "after_parking": parking_instructions_given},
            )
            return (
                "बहुत बढ़िया! अब वाहन की इग्निशन ऑन करें।\n"
                "Excellent! Now turn on the vehicle ignition.\n\n"
                "इग्निशन ऑन करने के बाद '1' दबाएं।\n"
                "Press '1' after turning on the ignition.\n\n"
                "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
            )

        if normalized in ["2", "not found", "नहीं मिला"]:
            # If cut out not found, proceed to ignition directly
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_IGNITION)
            # Clear the parking instruction flag as we're moving to next step
            state_manager.update_context(user.phone_number, {"parking_instructions_given": False})
            logger.info(
                "Cut out not found - proceeding directly to ignition",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_IGNITION.value},
            )
            return (
                "कोई बात नहीं। सीधे इग्निशन ऑन करते हैं।\n"
                "No problem. Let's turn on the ignition directly.\n\n"
                "वाहन की इग्निशन ऑन करें।\n"
                "Turn on the vehicle ignition.\n\n"
                "इग्निशन ऑन करने के बाद '1' दबाएं।\n"
                "Press '1' after turning on the ignition.\n\n"
                "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
            )

        logger.warning(
            "Invalid cut out response - expecting confirmation",
            extra={"phone_number": user.phone_number, "text": text_body, "ignition_was_on": ignition_was_on, "parking_instructions_given": parking_instructions_given},
        )
        
        # Show appropriate options based on current state
        if ignition_was_on and not parking_instructions_given:
            # Show initial driving scenario options
            return (
                "कृपया वैध विकल्प चुनें।\n"
                "Please select a valid option.\n\n"
                "क्या आप अभी गाड़ी चला रहे हैं?\n"
                "Are you currently driving?\n\n"
                "1️⃣ मैं वाहन पार्क कर दूंगा / I'll park the vehicle\n"
                "2️⃣ मैं ड्राइविंग नहीं कर रहा / I'm not driving"
            )
        elif ignition_was_on and parking_instructions_given:
            # Show completion options after parking instructions given
            return (
                "कृपया वैध विकल्प चुनें।\n"
                "Please select a valid option.\n\n"
                "दोनों बंद करने के बाद:\n"
                "After turning off both:\n\n"
                "1️⃣ इग्निशन और कट आउट दोनों बंद कर दिया / Both ignition and cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )
        else:
            # Show normal cut out options (when ignition was already off)
            return (
                "कृपया वैध विकल्प चुनें।\n"
                "Please select a valid option.\n\n"
                "पहले वाहन का कट आउट बंद करें।\n"
                "First turn off the vehicle cut out.\n\n"
                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )

    # GPS Repair Flow - Handle ignition confirmation with verification
    if current_step == ConversationStep.GPS_REPAIR_IGNITION.value:
        if normalized in ["1", "done", "ignition on", "ok"]:
            # Verify ignition state using API before proceeding
            vehicle_number = _get_vehicle_number_for_user(user.phone_number, db)
            if not vehicle_number:
                logger.warning(f"Cannot verify ignition - no vehicle found for user {user.phone_number}")
                # Proceed without verification if can't get vehicle
                state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_VERIFICATION)
                logger.info(
                    "GPS repair ignition step completed (no verification) - starting automatic GPS verification",
                    extra={"phone_number": user.phone_number}
                )
                # Continue with original flow
                initial_response = (
                    "बहुत बढ़िया! इग्निशन ऑन करने के बाद GPS सिस्टम को काम करना शुरू कर देना चाहिए।\n"
                    "Excellent! After turning on the ignition, the GPS system should start working.\n\n"
                    "🔍 GPS स्थिति की जांच की जा रही है... कृपया प्रतीक्षा करें।\n"
                    "🔍 Checking GPS status... Please wait."
                )
                try:
                    send_whatsapp_message(user.phone_number, initial_response)
                except Exception as e:
                    logger.error(f"Failed to send initial verification message: {str(e)}")
                
                if db:
                    verification_result = _perform_gps_verification(user.phone_number, db, state_manager)
                    return verification_result
                else:
                    state_manager.clear_state(user.phone_number)
                    return initial_response

            try:
                from app.services.vehicle_status_service import VehicleStatusService
                status_service = VehicleStatusService(db)
                vehicle_status = status_service.get_vehicle_status(vehicle_number)
                
                if not vehicle_status:
                    logger.warning(f"No vehicle status available for ignition verification - {vehicle_number}")
                    # Proceed without verification if status unavailable
                    state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_VERIFICATION)
                    logger.info("Proceeding with GPS verification without ignition check")
                    initial_response = (
                        "इग्निशन स्थिति की जांच नहीं हो सकी। GPS जांच के साथ आगे बढ़ रहे हैं।\n"
                        "Could not check ignition status. Proceeding with GPS check.\n\n"
                        "🔍 GPS स्थिति की जांच की जा रही है... कृपया प्रतीक्षा करें।\n"
                        "🔍 Checking GPS status... Please wait."
                    )
                    try:
                        send_whatsapp_message(user.phone_number, initial_response)
                    except Exception as e:
                        logger.error(f"Failed to send verification message: {str(e)}")
                    
                    if db:
                        verification_result = _perform_gps_verification(user.phone_number, db, state_manager)
                        return verification_result
                    else:
                        state_manager.clear_state(user.phone_number)
                        return initial_response
                
                current_ignition = vehicle_status.get("ignition_state", "").lower()
                logger.info(
                    f"Ignition verification for vehicle {vehicle_number}: expected=on, actual={current_ignition}",
                    extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number, "ignition_state": current_ignition}
                )
                
                if current_ignition == "on":
                    # Ignition is verified as ON - proceed with GPS verification
                    state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_VERIFICATION)
                    logger.info(
                        "Ignition verified as ON - proceeding with GPS verification",
                        extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number}
                    )
                    
                    initial_response = (
                        "बहुत बढ़िया! हमें दिख रहा है कि इग्निशन सफलतापूर्वक चालू है।\n"
                        "Excellent! We can see that the ignition is successfully turned on.\n\n"
                        "अब GPS सिस्टम को काम करना शुरू कर देना चाहिए।\n"
                        "Now the GPS system should start working.\n\n"
                        "🔍 GPS स्थिति की जांच की जा रही है... कृपया प्रतीक्षा करें।\n"
                        "🔍 Checking GPS status... Please wait."
                    )
                    
                    # Send initial message first
                    try:
                        send_whatsapp_message(user.phone_number, initial_response)
                    except Exception as e:
                        logger.error(f"Failed to send verification message: {str(e)}")
                    
                    # Perform automatic GPS verification
                    if db:
                        verification_result = _perform_gps_verification(user.phone_number, db, state_manager)
                        return verification_result
                    else:
                        state_manager.clear_state(user.phone_number)
                        return initial_response
                        
                else:
                    # Ignition is still OFF - ask driver to turn it on
                    logger.warning(
                        f"Ignition verification failed - still OFF for vehicle {vehicle_number}",
                        extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number, "ignition_state": current_ignition}
                    )
                    # Stay in same state - don't proceed until ignition is actually on
                    return (
                        "⚠️ हमें दिख रहा है कि आपके वाहन की इग्निशन अभी भी बंद है।\n"
                        "⚠️ We can see that your vehicle ignition is still off.\n\n"
                        "कृपया सुनिश्चित करें कि आप इग्निशन को पूरी तरह से ऑन कर रहे हैं।\n"
                        "Please make sure you are turning the ignition completely on.\n\n"
                        "इग्निशन ऑन करने के बाद '1' दबाएं।\n"
                        "Press '1' after turning on the ignition.\n\n"
                        "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
                    )
                    
            except Exception as e:
                logger.error(
                    f"Error during ignition verification for user {user.phone_number}: {str(e)}",
                    extra={"phone_number": user.phone_number, "vehicle_number": vehicle_number},
                    exc_info=True
                )
                # Proceed with GPS verification on error
                state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_VERIFICATION)
                logger.info("Proceeding with GPS verification after ignition check error")
                
                initial_response = (
                    "इग्निशन जांच में त्रुटि हुई। GPS जांच के साथ आगे बढ़ रहे हैं।\n"
                    "Error in ignition check. Proceeding with GPS check.\n\n"
                    "🔍 GPS स्थिति की जांच की जा रही है... कृपया प्रतीक्षा करें।\n"
                    "🔍 Checking GPS status... Please wait."
                )
                try:
                    send_whatsapp_message(user.phone_number, initial_response)
                except Exception as e2:
                    logger.error(f"Failed to send error recovery message: {str(e2)}")
                
                if db:
                    verification_result = _perform_gps_verification(user.phone_number, db, state_manager)
                    return verification_result
                else:
                    state_manager.clear_state(user.phone_number)
                    return initial_response

        logger.warning(
            "Invalid ignition response - expecting confirmation",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया इग्निशन ऑन करने के बाद '1' दबाएं।\n"
            "Please press '1' after turning on the ignition.\n\n"
            "1️⃣ इग्निशन ऑन कर दिया / Ignition turned on"
        )

    # GPS Repair Flow - Handle verification state (user shouldn't normally reach this)
    if current_step == ConversationStep.GPS_REPAIR_VERIFICATION.value:
        # If user sends a message during verification, just inform them to wait
        logger.info(
            "User sent message during GPS verification - asking them to wait",
            extra={"phone_number": user.phone_number, "text": text_body}
        )
        return (
            "🔍 GPS सत्यापन चल रहा है, कृपया कुछ सेकंड प्रतीक्षा करें।\n"
            "🔍 GPS verification in progress, please wait a few seconds.\n\n"
            "हम स्वचालित रूप से आपके वाहन की स्थिति जांच रहे हैं।\n"
            "We are automatically checking your vehicle status."
        )

    # GPS Repair Flow - Handle callback scheduling
    if current_step == ConversationStep.GPS_REPAIR_SCHEDULE_CALLBACK.value:
        if normalized in ["1", "go to vehicle", "जा सकता"]:
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_CUT_OUT)
            logger.info(
                "Driver will go to vehicle - proceeding to cut out step",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_CUT_OUT.value},
            )
            return (
                "बहुत अच्छा! वाहन के पास जाकर पहले कट आउट बंद करें।\n"
                "Great! Go to the vehicle and first turn off the cut out.\n\n"
                "कट आउट बंद करने के बाद '1' दबाएं।\n"
                "Press '1' after turning off the cut out.\n\n"
                "1️⃣ कट आउट बंद कर दिया / Cut out turned off\n"
                "2️⃣ कट आउट नहीं मिला / Cut out not found"
            )

        if normalized in ["2", "call later", "बाद में"]:
            # Clear state and schedule callback (in real implementation, this could store callback time)
            state_manager.clear_state(user.phone_number)
            logger.info(
                "Driver requested callback later",
                extra={"phone_number": user.phone_number}
            )
            return (
                "ठीक है। हम आपको बाद में कॉल करेंगे।\n"
                "Okay. We will call you back later.\n\n"
                "कृपया बताएं कि हमें कितने घंटे बाद कॉल करना चाहिए? (जैसे: 1 घंटे बाद, 2 घंटे बाद)\n"
                "Please tell us how many hours later we should call? (Example: after 1 hour, after 2 hours)\n\n"
                "या आप जब वाहन के पास हों तो हमें कॉल कर सकते हैं।\n"
                "Or you can call us when you are near the vehicle."
            )

        logger.warning(
            "Invalid callback scheduling response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "1️⃣ मैं वाहन के पास जा सकता हूं / I can go to the vehicle\n"
            "2️⃣ बाद में कॉल करें / Call back later"
        )

    # GPS Repair Flow - Handle GPS re-verification requests after failed verification
    if current_step == ConversationStep.GPS_REPAIR_RECHECK.value:
        if normalized in ["1", "check again", "दोबारा", "recheck", "चेक"]:
            # User wants to trigger another GPS verification cycle
            state_manager.set_state(user.phone_number, ConversationStep.GPS_REPAIR_VERIFICATION)
            logger.info(
                "User requested GPS re-verification - starting new verification cycle",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.GPS_REPAIR_VERIFICATION.value}
            )
            
            # Trigger new GPS verification asynchronously with baseline comparison
            try:
                verification_result = _perform_gps_verification(user.phone_number, db, state_manager)
                return verification_result
            except Exception as e:
                logger.error(
                    f"Error during GPS re-verification for user {user.phone_number}: {str(e)}",
                    extra={"user_phone": user.phone_number},
                    exc_info=True
                )
                # Clear state on error
                state_manager.clear_state(user.phone_number)
                return (
                    "⚠️ GPS सत्यापन में त्रुटि हुई।\n"
                    "⚠️ Error occurred during GPS verification.\n\n"
                    "कृपया मैन्युअल रूप से GPS स्थिति जांच लें या फिर से संपर्क करें।\n"
                    "Please manually check GPS status or contact us again.\n\n"
                    "धन्यवाद! / Thank you!"
                )

        if normalized in ["2", "talk later", "बाद में", "later"]:
            # User wants to end conversation
            state_manager.clear_state(user.phone_number)
            logger.info(
                "User chose to end GPS repair conversation",
                extra={"phone_number": user.phone_number}
            )
            return (
                "ठीक है। GPS की समस्या बनी रहे तो कृपया हमसे संपर्क करें।\n"
                "Alright. If GPS issues persist, please contact us.\n\n"
                "हमारी तकनीकी टीम आपकी सहायता के लिए हमेशा तैयार है।\n"
                "Our technical team is always ready to help you.\n\n"
                "धन्यवाद! / Thank you!"
            )

        # Invalid response - show options again
        logger.warning(
            "Invalid GPS recheck response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "कृपया वैध विकल्प चुनें।\n"
            "Please select a valid option.\n\n"
            "1️⃣ दोबारा चेक करें / Check again\n"
            "2️⃣ बाद में बात करें / Talk later\n\n"
            "आपके GPS की स्थिति जांचने के लिए तैयार हैं।\n"
            "Ready to check your GPS status."
        )

    # Continue with existing diagnostic flow states
    if current_step == ConversationStep.VEHICLE_NUMBER.value:
        state_manager.update_context(user.phone_number, {"vehicle_number": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_DRIVER_AVAILABILITY.value},
        )
        return (
            "Kripya driver vehicle ke paas hai?\n"
            "1️⃣ Haan\n"
            "2️⃣ Nahi"
        )

    if current_step == ConversationStep.ASK_DRIVER_AVAILABILITY.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user.phone_number, {"driver_phone": user.phone_number})
            state_manager.set_state(user.phone_number, ConversationStep.ASK_LOCATION)
            logger.info(
                "State updated",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_LOCATION.value},
            )
            return "Bataiye vehicle ka location kya hai?"

        if _is_negative(normalized):
            state_manager.set_state(user.phone_number, ConversationStep.OWNER_CONFIRMATION)
            logger.info(
                "State updated",
                extra={"phone_number": user.phone_number, "new_state": ConversationStep.OWNER_CONFIRMATION.value},
            )
            return "Kripya owner ka naam aur phone number bhejiye."

        logger.warning(
            "Invalid driver availability response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return (
            "Kripya valid option select kare.\n"
            "1️⃣ Haan\n"
            "2️⃣ Nahi"
        )

    if current_step == ConversationStep.OWNER_CONFIRMATION.value:
        state_manager.update_context(user.phone_number, {"owner_name": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.DRIVER_HANDOFF)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.DRIVER_HANDOFF.value},
        )
        return "Thik hai. Kya aap driver handoff karna chahenge? Haan / Nahi"

    if current_step == ConversationStep.DRIVER_HANDOFF.value:
        if _is_affirmative(normalized):
            state_manager.update_context(user.phone_number, {"driver_name": "handoff_requested"})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_LOCATION)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_LOCATION.value},
        )
        return "Dhanyavaad. Machine ka location bataiye."

    if current_step == ConversationStep.ASK_LOCATION.value:
        state_manager.update_context(user.phone_number, {"location": text_body})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_IGNITION)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_IGNITION.value},
        )
        return "Kya ignition on hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_IGNITION.value:
        state_manager.update_context(user.phone_number, {"ignition_status": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_POWER_LED)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_POWER_LED.value},
        )
        return "Kya power LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_POWER_LED.value:
        state_manager.update_context(user.phone_number, {"power_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_GSM_LED)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_GSM_LED.value},
        )
        return "Kya GSM LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_GSM_LED.value:
        state_manager.update_context(user.phone_number, {"gsm_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.ASK_GPS_LED)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.ASK_GPS_LED.value},
        )
        return "Kya GPS LED jal rahi hai? Haan / Nahi"

    if current_step == ConversationStep.ASK_GPS_LED.value:
        state_manager.update_context(user.phone_number, {"gps_led": normalized})
        state_manager.set_state(user.phone_number, ConversationStep.VERIFY_RESOLUTION)
        logger.info(
            "State updated",
            extra={"phone_number": user.phone_number, "new_state": ConversationStep.VERIFY_RESOLUTION.value},
        )
        return "Kya problem solve ho gayi? Haan / Nahi"

    if current_step == ConversationStep.VERIFY_RESOLUTION.value:
        if _is_affirmative(normalized):
            state_manager.clear_state(user.phone_number)
            logger.info("State cleared after resolution", extra={"phone_number": user.phone_number})
            return "Bahut achha. Agar kuch aur madad chahiye toh bataiye."

        if _is_negative(normalized):
            ticket = create_ticket(
                customer_phone=user.phone_number,
                problem=context.get("issue_type", "vehicle_problem"),
                driver_phone=context.get("driver_phone"),
                customer_id=user.id,
            )
            state_manager.update_context(user.phone_number, {"ticket_id": ticket.ticket_number})
            state_manager.set_state(user.phone_number, ConversationStep.TICKET_CONFIRMATION)
            logger.info(
                "Ticket created",
                extra={"phone_number": user.phone_number, "ticket_number": ticket.ticket_number},
            )
            return (
                f"Theek hai. Ticket {ticket.ticket_number} create kar diya gaya hai.\n"
                "Engineer jaldi contact karega."
            )

        logger.warning(
            "Invalid resolution response",
            extra={"phone_number": user.phone_number, "text": text_body},
        )
        return "Kripya sirf Haan ya Nahi mein reply dein. Kya problem solve hui?"

    if current_step == ConversationStep.TICKET_CONFIRMATION.value:
        if _is_affirmative(normalized):
            state_manager.clear_state(user.phone_number)
            return "Great. Agar aapko aur madad chahiye toh dobara message karein."
        return "Aap chahte hain ki engineer turant bheja jaaye."

    # Default fallback - show main menu
    logger.debug("Transitioning unknown state %s to MAIN_MENU", current_step)
    greeting_service.route_to_main_menu(user.phone_number)
    return greeting_service.send_welcome(user.name)
