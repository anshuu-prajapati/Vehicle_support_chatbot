"""
Flow Router Service

Routes incoming messages to appropriate flow handler:
- Old GPS repair flow (for backward compatibility)
- New service engineer assignment flow (primary)
"""
import logging
from sqlalchemy.orm import Session
from app.services.state_manager import StateManager, ConversationStep

logger = logging.getLogger("app.flow_router")

# Old GPS repair flow states (for backward compatibility)
OLD_GPS_REPAIR_STATES = {
    ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value,
    ConversationStep.GPS_REPAIR_TIME_ESTIMATE.value,
    ConversationStep.GPS_REPAIR_WAITING_FOR_DRIVER.value,
    ConversationStep.GPS_REPAIR_CHECK_IGNITION.value,
    ConversationStep.GPS_REPAIR_CUT_OUT.value,
    ConversationStep.GPS_REPAIR_IGNITION.value,
    ConversationStep.GPS_REPAIR_VERIFICATION.value,
    ConversationStep.GPS_REPAIR_RECHECK.value,
    ConversationStep.GPS_REPAIR_GROUND_WIRE_FIND.value,
    ConversationStep.GPS_REPAIR_GROUND_WIRE_TOUCH.value,
    ConversationStep.GPS_REPAIR_GROUND_WIRE_VERIFY.value,
    ConversationStep.GPS_REPAIR_FINAL_CHECK.value,
    ConversationStep.GPS_REPAIR_ENGINEER_DISPATCH.value,
    ConversationStep.GPS_REPAIR_SCHEDULE_CALLBACK.value,
}

# New service engineer assignment flow states (Enhanced Flow Q2-Q35)
NEW_SERVICE_ENGINEER_STATES = {
    # Initial & Classification
    ConversationStep.INITIAL_CUSTOMER_MESSAGE.value,
    ConversationStep.INTENT_CLASSIFICATION.value,
    
    # Workshop/Accident/Battery Flows (Q2-Q4)
    ConversationStep.WORKSHOP_CONFIRMATION.value,
    ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION.value,
    ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION.value,
    
    # GPS Removed Flow (Q5-Q9)
    ConversationStep.GPS_REMOVED_REINSTALL_DATE.value,
    ConversationStep.GPS_REMOVED_LOCATION.value,
    ConversationStep.GPS_REMOVED_CONTACT.value,
    ConversationStep.GPS_REMOVED_AVAILABILITY.value,
    ConversationStep.GPS_REMOVED_AVAILABLE_DATE.value,
    
    # GPS Damaged Flow (Q10-Q12)
    ConversationStep.GPS_DAMAGED_LOCATION.value,
    ConversationStep.GPS_DAMAGED_CONTACT.value,
    ConversationStep.GPS_DAMAGED_INSPECTION_DATE.value,
    
    # Vehicle Running Flow (Q13-Q16)
    ConversationStep.VEHICLE_RUNNING_DRIVER_NAME.value,
    ConversationStep.VEHICLE_RUNNING_DRIVER_MOBILE.value,
    ConversationStep.VEHICLE_RUNNING_LOCATION.value,
    ConversationStep.VEHICLE_RUNNING_INSPECTION_DATE.value,
    
    # Vehicle Standing Flow (Q17-Q19)
    ConversationStep.VEHICLE_STANDING_DURATION.value,
    ConversationStep.VEHICLE_STANDING_LOCATION.value,
    ConversationStep.VEHICLE_STANDING_INSPECTION_DATE.value,
    
    # Other/Unknown Flow (Q20)
    ConversationStep.OTHER_ISSUE_DESCRIPTION.value,
    
    # Service Request Data Collection (Q25-Q34)
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
    
    # Engineer Assignment (Q35)
    ConversationStep.ENGINEER_ASSIGNMENT.value,
}


def route_message(user, text_body: str, state_manager: StateManager, db: Session) -> str:
    """
    Route message to appropriate flow handler based on conversation state.
    
    Routing Logic:
    1. If user is in OLD GPS repair state → Use old GPS repair flow
    2. If user is in NEW service engineer state → Use new service engineer flow
    3. If user is in greeting/menu state → Use new service engineer flow (default)
    4. For any other state → Use new service engineer flow
    
    Args:
        user: User object with phone_number
        text_body: Message text from user
        state_manager: StateManager instance
        db: Database session
        
    Returns:
        Response message to send to user
    """
    state = state_manager.get_state(user.phone_number)
    
    # Determine which flow to use
    if state and state.current_step in OLD_GPS_REPAIR_STATES:
        # Route to old GPS repair flow (backward compatibility)
        logger.info(
            f"Routing to OLD GPS repair flow",
            extra={
                "phone_number": user.phone_number,
                "current_step": state.current_step,
                "flow": "OLD_GPS_REPAIR"
            }
        )
        from app.services.support_flow_service import handle_support_message as handle_gps_repair_flow
        return handle_gps_repair_flow(user, text_body, state_manager, db)
    
    else:
        # Route to new service engineer flow (default for all new conversations)
        logger.info(
            f"Routing to NEW service engineer flow",
            extra={
                "phone_number": user.phone_number,
                "current_step": state.current_step if state else "None",
                "flow": "NEW_SERVICE_ENGINEER"
            }
        )
        # Import here to avoid circular dependency
        # Will be created in next step
        try:
            from app.services.service_engineer_flow_service import handle_service_engineer_message
            return handle_service_engineer_message(user, text_body, state_manager, db)
        except ImportError:
            # Fallback to old flow if new flow not yet implemented
            logger.warning(
                "New service engineer flow not yet implemented, falling back to old flow",
                extra={"phone_number": user.phone_number}
            )
            from app.services.support_flow_service import handle_support_message as handle_gps_repair_flow
            return handle_gps_repair_flow(user, text_body, state_manager, db)


def is_old_flow_state(current_step: str) -> bool:
    """
    Check if current step belongs to old GPS repair flow.
    
    Args:
        current_step: Current conversation step
        
    Returns:
        True if old flow state, False otherwise
    """
    return current_step in OLD_GPS_REPAIR_STATES


def is_new_flow_state(current_step: str) -> bool:
    """
    Check if current step belongs to new service engineer flow.
    
    Args:
        current_step: Current conversation step
        
    Returns:
        True if new flow state, False otherwise
    """
    return current_step in NEW_SERVICE_ENGINEER_STATES


def get_flow_type(user_phone: str, state_manager: StateManager) -> str:
    """
    Get the current flow type for a user.
    
    Args:
        user_phone: User's phone number
        state_manager: StateManager instance
        
    Returns:
        Flow type: "OLD_GPS_REPAIR", "NEW_SERVICE_ENGINEER", or "UNKNOWN"
    """
    state = state_manager.get_state(user_phone)
    
    if not state:
        return "NEW_SERVICE_ENGINEER"  # Default for new conversations
    
    if state.current_step in OLD_GPS_REPAIR_STATES:
        return "OLD_GPS_REPAIR"
    elif state.current_step in NEW_SERVICE_ENGINEER_STATES:
        return "NEW_SERVICE_ENGINEER"
    else:
        # For menu, greeting, or other states - default to new flow
        return "NEW_SERVICE_ENGINEER"
