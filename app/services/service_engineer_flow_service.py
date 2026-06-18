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
from app.services.general_conversation_handler import handle_general_conversation
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
            "Dhanyavaad. 🙏\n\n"
            "Vehicle ke dobara operational hone ki expected date kya hai?"
        )
    
    elif issue_type == "ACCIDENT":
        state_manager.set_state(user_phone, ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION)
        return (
            "Dhanyavaad. 🙏\n\n"
            "Kya vehicle filhaal workshop ya repair center mein hai?"
        )
    
    elif issue_type == "BATTERY_DISCONNECT":
        state_manager.set_state(user_phone, ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION)
        return (
            "Dhanyavaad. 🙏\n\n"
            "Vehicle ya battery system dobara kab operational hoga?\n\n"
            "Example: 20-06-2026"
        )
    
    elif issue_type == "GPS_REMOVED":
        state_manager.set_state(user_phone, ConversationStep.GPS_REMOVED_REINSTALL_DATE)
        return (
            "Dhanyavaad. 🙏\n\n"
            "GPS re-installation kab karwana hai?\n\n"
            "Example: 20-06-2026"
        )
    
    elif issue_type == "GPS_DAMAGED":
        state_manager.set_state(user_phone, ConversationStep.GPS_DAMAGED_LOCATION)
        state_manager.update_context(user_phone, {
            "gps_damaged_sub_step": "GPS_DAMAGED_LOCATION"
        })
        return (
            "Dhanyavaad. 🙏\n\n"
            "Humne note kar liya hai ki GPS device damage ho gaya hai.\n\n"
            "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
            "📍 Example: Kirti Nagar, Delhi"
        )
    
    elif issue_type == "VEHICLE_RUNNING":
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_RUNNING_DRIVER_NAME)
        return (
            "Dhanyavaad. 🙏\n\n"
            "Hum samajh gaye hain ki vehicle chal rahi hai lekin GPS data receive nahi ho raha.\n\n"
            "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
            "📍 Example: Kirti Nagar, Delhi"
        )
    
    elif issue_type == "VEHICLE_STANDING":
        state_manager.set_state(user_phone, ConversationStep.VEHICLE_STANDING_DURATION)
        return (
            "Dhanyavaad. 🙏\n\n"
            "Kya aap bata sakte hain vehicle kab se standing condition mein hai?\n\n"
            "📅 Examples:\n"
            "• Aaj se\n"
            "• Kal se\n"
            "• 1 din se\n"
            "• 2 din se\n"
            "• 3 din se\n"
            "• Ek hafte se"
        )
    
    else:  # UNKNOWN or OTHER
        state_manager.set_state(user_phone, ConversationStep.OTHER_ISSUE_DESCRIPTION)
        return (
            "Samajhne ke liye kripya thoda aur detail mein batayein ki vehicle ya GPS ke saath kya issue aa raha hai.\n\n"
            "Aap normal language mein bata sakte hain."
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
    context = state_manager.get_context(user.phone_number)
    
    # Get vehicle information for context
    vehicle_number = context.get("vehicle_number") if context else None
    if not vehicle_number:
        vehicle_number = _get_vehicle_number_for_user(user.phone_number, db)
    
    last_location = context.get("last_location") if context else None
    
    # === GENERAL CONVERSATION LAYER ===
    # Check if this is general conversation (questions, greetings, clarifications)
    # BEFORE routing to issue classification
    
    logger.info(
        f"🔍 FLOW ENTRY POINT - Processing message for {user.phone_number}",
        extra={
            "user_phone": user.phone_number,
            "message": text_body,
            "message_normalized": normalized,
            "current_state": state.current_step if state else "NO_STATE",
            "has_context": bool(context),
            "vehicle_number": vehicle_number
        }
    )
    
    is_general, general_response = handle_general_conversation(
        text=text_body,
        current_step=state.current_step if state else None,
        context=context,
        vehicle_number=vehicle_number,
        last_location=last_location
    )
    
    if is_general:
        logger.warning(
            f"⚠️ GENERAL CONVERSATION DETECTED - Intercepted by general_conversation_handler",
            extra={
                "user_phone": user.phone_number,
                "message": text_body[:100],
                "current_step": state.current_step if state else "None",
                "response_preview": general_response[:100] if general_response else "None"
            }
        )
        # Return general response WITHOUT changing conversation state
        return general_response
    
    logger.info(
        f"✅ NOT general conversation - proceeding to intent classification",
        extra={
            "user_phone": user.phone_number,
            "message": text_body[:50]
        }
    )
    
    # === END GENERAL CONVERSATION LAYER ===
    
    # === ORCHESTRATOR INTEGRATION - FIRST REPLY AFTER GPS ALERT ===
    # Use orchestrator as first intelligence layer for initial GPS alert replies
    # This provides smart entity extraction and context handling
    # CRITICAL: Once orchestrator starts handling a conversation, it continues
    # until ticket is created or conversation is reset
    orchestrator_is_active = context and context.get("orchestrator_active")
    orchestrator_should_start = not state or state.current_step == ConversationStep.MAIN_MENU.value
    
    if orchestrator_should_start or orchestrator_is_active:
        if orchestrator_is_active:
            logger.info(
                f"🎯 ORCHESTRATOR CONTINUATION - Processing follow-up message",
                extra={
                    "user_phone": user.phone_number,
                    "message": text_body,
                    "vehicle_number": vehicle_number,
                    "orchestrator_active": True
                }
            )
        else:
            logger.info(
                f"🎯 ORCHESTRATOR ENTRY POINT - First reply after GPS alert",
                extra={
                    "user_phone": user.phone_number,
                    "message": text_body,
                    "vehicle_number": vehicle_number
                }
            )
        
        # Try orchestrator first for intelligent processing
        try:
            from app.services.service_request_orchestrator import process_gps_alert_reply
            
            logger.info(f"[ORCHESTRATOR] Processing message through orchestrator")
            
            orchestrator_response, service_request = process_gps_alert_reply(
                message=text_body,
                vehicle_number=vehicle_number or "UNKNOWN",
                user_phone=user.phone_number,
                conversation_history=None,
                db=db
            )
            
            # Log orchestrator results
            logger.info(
                f"[ORCHESTRATOR] Intent detected: {service_request.get('issue_type')}",
                extra={
                    "user_phone": user.phone_number,
                    "intent": service_request.get('issue_type'),
                    "case_closed": service_request.get('case_closed'),
                    "service_required": service_request.get('service_required'),
                    "ticket_created": service_request.get('ticket_created')
                }
            )
            
            logger.info(
                f"[ORCHESTRATOR] Extracted entities",
                extra={
                    "user_phone": user.phone_number,
                    "origin_city": service_request.get('origin_city'),
                    "destination_city": service_request.get('destination_city'),
                    "service_location": service_request.get('service_location'),
                    "service_date": service_request.get('service_date'),
                    "phone": service_request.get('phone'),
                    "contact_person": service_request.get('contact_person')
                }
            )
            
            # Determine missing fields
            missing_fields = []
            if not service_request.get('service_location') and not service_request.get('destination_city'):
                missing_fields.append('location')
            if not service_request.get('service_date'):
                missing_fields.append('service_date')
            if not service_request.get('phone'):
                missing_fields.append('phone')
            
            logger.info(
                f"[ORCHESTRATOR] Missing fields: {missing_fields}",
                extra={
                    "user_phone": user.phone_number,
                    "missing_fields": missing_fields
                }
            )
            
            # Update context with orchestrator data
            state_manager.update_context(user.phone_number, {
                "orchestrator_service_request": service_request,
                "orchestrator_active": True,
                "vehicle_number": vehicle_number or service_request.get('vehicle_number')
            })
            
            # Route based on orchestrator decision
            if service_request.get('case_closed'):
                # Case closed - use orchestrator response, but also route to existing handler
                issue_type = service_request.get('issue_type', 'UNKNOWN')
                
                logger.info(
                    f"[ORCHESTRATOR] ROUTING DECISION: Case closed - {issue_type}",
                    extra={
                        "user_phone": user.phone_number,
                        "issue_type": issue_type,
                        "case_closed": True
                    }
                )
                
                # Map orchestrator case types to existing flow types
                case_type_map = {
                    "workshop": "WORKSHOP",
                    "accident": "ACCIDENT",
                    "battery_disconnect": "BATTERY_DISCONNECT",
                    "gps_removed_maintenance": "GPS_REMOVED"
                }
                
                flow_type = case_type_map.get(issue_type, "UNKNOWN")
                
                # Store classification in context
                state_manager.update_context(user.phone_number, {
                    "issue_classification": flow_type,
                    "classification_method": "ORCHESTRATOR_CASE_CLOSED",
                    "customer_response": text_body
                })
                
                # Return orchestrator response (already handles case closed scenarios)
                return orchestrator_response
            
            elif service_request.get('service_required'):
                issue_type = service_request.get('issue_type', 'other_gps_issue')
                
                # If ticket created, route to existing service flow with extracted entities
                if service_request.get('ticket_created'):
                    logger.info(
                        f"[ORCHESTRATOR] ROUTING DECISION: Ticket ready - {issue_type}",
                        extra={
                            "user_phone": user.phone_number,
                            "issue_type": issue_type,
                            "ticket_created": True,
                            "all_fields_collected": True
                        }
                    )
                    
                    # === CREATE ACTUAL TICKET ===
                    try:
                        # Prepare ticket data from service request
                        location = (service_request.get('service_location') 
                                   or service_request.get('destination_city')
                                   or service_request.get('origin_city')
                                   or "Location not specified")
                        
                        # Build problem description with all details
                        # (dates/times from orchestrator are natural language like "kal", "3 PM")
                        problem_desc = f"{issue_type} - {service_request.get('issue_type', 'GPS Issue')}"
                        if service_request.get('service_date'):
                            problem_desc += f" | Service Date: {service_request.get('service_date')}"
                        if service_request.get('service_time'):
                            problem_desc += f" | Time: {service_request.get('service_time')}"
                        
                        # Create the ticket
                        # Note: visit_date/visit_time expect Date/Time objects, but orchestrator
                        # returns natural language strings ("kal", "3 PM"). We pass None to these
                        # fields and include the info in problem description instead.
                        ticket = create_service_request_ticket(
                            vehicle_number=vehicle_number or "UNKNOWN",
                            issue_type=issue_type.upper(),
                            customer_phone=user.phone_number,
                            location=location,
                            visit_date=None,  # Orchestrator returns strings like "kal", not Date objects
                            visit_time=None,  # Orchestrator returns strings like "3 PM", not Time objects
                            driver_mobile=service_request.get('phone'),
                            driver_name=service_request.get('contact_person'),
                            owner_mobile=service_request.get('phone'),
                            problem=problem_desc
                        )
                        
                        logger.info(
                            f"[ORCHESTRATOR] Ticket created successfully",
                            extra={
                                "user_phone": user.phone_number,
                                "ticket_number": ticket.ticket_number,
                                "ticket_id": ticket.id
                            }
                        )
                        
                        # Update context with ticket info
                        state_manager.update_context(user.phone_number, {
                            "service_request_id": ticket.ticket_number,
                            "ticket_id": ticket.id
                        })
                        
                        # === ENHANCED RESPONSE WITH TICKET ID ===
                        # Build response with ticket details
                        enhanced_response = (
                            f"✅ Service request create kar di gayi hai!\n\n"
                            f"📋 *Ticket Details:*\n"
                            f"🎫 Ticket ID: *{ticket.ticket_number}*\n"
                            f"📍 Location: {location}\n"
                            f"📅 Service Date: {service_request.get('service_date', 'As per availability')}\n"
                        )
                        
                        if service_request.get('service_time'):
                            enhanced_response += f"🕐 Time: {service_request.get('service_time')}\n"
                        
                        enhanced_response += f"📞 Contact: {service_request.get('phone', user.phone_number)}\n\n"
                        
                        # Check if engineer is already assigned (future enhancement)
                        if ticket.assigned_engineer:
                            enhanced_response += (
                                f"👤 *Assigned Engineer:*\n"
                                f"Name: {ticket.assigned_engineer.name}\n"
                                f"Phone: {ticket.assigned_engineer.phone_number}\n\n"
                            )
                        else:
                            enhanced_response += (
                                f"👤 Engineer assignment jald ho jayega.\n\n"
                            )
                        
                        enhanced_response += (
                            f"Engineer aapse jald sampark karega.\n"
                            f"Koi sawal ho toh Ticket ID {ticket.ticket_number} ke saath humse sampark karein.\n\n"
                            f"Dhanyavaad!"
                        )
                        
                        # Clear orchestrator state after successful ticket creation
                        state_manager.clear_state(user.phone_number)
                        
                        return enhanced_response
                        
                    except Exception as ticket_error:
                        logger.error(
                            f"[ORCHESTRATOR] Ticket creation failed: {str(ticket_error)}",
                            extra={
                                "user_phone": user.phone_number,
                                "error": str(ticket_error)
                            },
                            exc_info=True
                        )
                        
                        # Fallback to orchestrator response if ticket creation fails
                        return (
                            orchestrator_response + 
                            "\n\n⚠️ Ticket ID generate mein issue hai. "
                            "Support team se sampark kiya ja raha hai."
                        )
                    # === END TICKET CREATION ===
                
                else:
                    # Still collecting information - return orchestrator question
                    logger.info(
                        f"[ORCHESTRATOR] ROUTING DECISION: Collecting information - {issue_type}",
                        extra={
                            "user_phone": user.phone_number,
                            "issue_type": issue_type,
                            "missing_fields": missing_fields
                        }
                    )
                    
                    # Return orchestrator response (asking for missing fields)
                    return orchestrator_response
            
            else:
                # Orchestrator couldn't determine - fall through to existing logic
                logger.info(
                    f"[ORCHESTRATOR] ROUTING DECISION: Unclear - falling back to existing logic",
                    extra={
                        "user_phone": user.phone_number,
                        "orchestrator_unclear": True
                    }
                )
        
        except Exception as e:
            # Orchestrator failed - fall through to existing logic
            logger.warning(
                f"[ORCHESTRATOR] Failed to process, falling back to existing logic: {str(e)}",
                extra={
                    "user_phone": user.phone_number,
                    "error": str(e)
                },
                exc_info=True
            )
    
    # === END ORCHESTRATOR INTEGRATION ===
    # Continue with existing logic as fallback
    
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
            # Check if user is indicating they don't know
            dont_know_keywords = [
                "pta ni", "pata nahi", "malum nahi", "not sure", "no idea",
                "cant say", "can't say", "nahi pata", "samajh nahi", "confused",
                "mujhe nahi pata", "kya issue hai", "pata nahi kya", "dont know", "don't know"
            ]
            
            is_dont_know = any(keyword in normalized for keyword in dont_know_keywords)
            
            if is_dont_know:
                logger.info(f"User {user.phone_number} doesn't know the issue - entering clarification mode")
                
                # Store in context and route to OTHER/clarification
                state_manager.update_context(user.phone_number, {
                    "issue_classification": "UNKNOWN",
                    "classification_method": "DONT_KNOW",
                    "customer_response": text_body,
                    "clarification_needed": True
                })
                
                state_manager.set_state(user.phone_number, ConversationStep.OTHER_ISSUE_DESCRIPTION)
                
                return (
                    "Koi baat nahi. 🙏\n\n"
                    "Kripya thoda aur bataiye:\n\n"
                    "Vehicle abhi chal rahi hai, khadi hai, workshop mein hai ya GPS se judi koi samasya aa rahi hai?\n\n"
                    "Aap normal language mein bata sakte hain."
                )
            
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
            
            # Classification returned UNKNOWN - route to clarification (OTHER flow)
            logger.info(f"Could not classify '{text_body[:50]}' - routing to clarification mode")
            
            state_manager.update_context(user.phone_number, {
                "issue_classification": "UNKNOWN",
                "classification_method": "UNCLEAR",
                "customer_response": text_body,
                "clarification_needed": True
            })
            
            state_manager.set_state(user.phone_number, ConversationStep.OTHER_ISSUE_DESCRIPTION)
            
            return (
                "Samajhne ke liye kripya thoda aur detail mein batayein ki vehicle ya GPS ke saath kya issue aa raha hai.\n\n"
                "Aap normal language mein bata sakte hain."
            )
        
        # If we reach here, it's not a number, not natural language we could classify
        # Ask user to provide proper input
        logger.warning(
            f"User {user.phone_number} sent unclassifiable input at MAIN_MENU: '{text_body[:50]}'",
            extra={"phone": user.phone_number, "message": text_body[:100]}
        )
        
        return (
            "⚠️ कृपया दिए गए विकल्पों में से चुनें या अपनी समस्या स्पष्ट रूप से बताएं।\n"
            "⚠️ Please choose from the given options or clearly describe your issue.\n\n"
            "विकल्प / Options:\n"
            "1️⃣ Workshop / Service Center\n"
            "2️⃣ Accident\n"
            "3️⃣ Battery Disconnect\n"
            "4️⃣ GPS Removed\n"
            "5️⃣ GPS Damaged\n"
            "6️⃣ Vehicle Running but GPS Not Updating\n"
            "7️⃣ Vehicle Standing\n"
            "8️⃣ Other\n\n"
            "या अपनी समस्या अपने शब्दों में बताएं।\n"
            "Or describe your problem in your own words."
        )
    
    # Check if we have an active state
    if not state:
        # No state and not at MAIN_MENU - this shouldn't happen
        # Try to classify and route without welcome message
        logger.warning(f"No state found for user {user.phone_number}, attempting classification")
        
        issue_type, method = classify_customer_intent(text_body)
        
        if issue_type != "UNKNOWN":
            logger.info(
                f"Classified message without state: {issue_type}",
                extra={"phone": user.phone_number, "message": text_body[:100]}
            )
            
            state_manager.update_context(user.phone_number, {
                "issue_classification": issue_type,
                "classification_method": f"NLP_{method}_NO_STATE",
                "customer_response": text_body
            })
            
            return _route_to_flow_handler(user.phone_number, issue_type, state_manager, db)
        
        # Could not classify - ask for proper input
        return (
            "⚠️ कृपया अपनी समस्या स्पष्ट रूप से बताएं।\n"
            "⚠️ Please describe your issue clearly.\n\n"
            "उदाहरण / Examples:\n"
            "• GPS खराब हो गया है / GPS is damaged\n"
            "• गाड़ी चल रही है पर tracking नहीं आ रही / Vehicle running but no tracking\n"
            "• GPS निकाल दिया है / GPS has been removed\n"
            "• गाड़ी workshop में है / Vehicle is in workshop"
        )
    
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
