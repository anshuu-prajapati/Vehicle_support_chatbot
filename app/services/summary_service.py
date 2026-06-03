import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import ChatMessage
from app.services.ai_response_service import generate_ai_answer

logger = logging.getLogger(__name__)


def build_investigation_summary(phone_number: str, context: Dict[str, Any]) -> str:
    """Build a summary of the driver investigation."""
    investigation = context.get("driver_investigation", {})
    vehicle = context.get("vehicle_number", "Unknown")
    driver_name = context.get("driver_name", "Driver")
    
    if not investigation:
        return f"No investigation data for {vehicle}"
    
    stop_reason = investigation.get("stop_reason", "Unknown").title()
    location = investigation.get("current_location", "Unknown")
    needs_mechanic = investigation.get("needs_mechanic", False)
    restart_time = investigation.get("expected_restart_time", "Unknown")
    
    summary = (
        f"📋 **VEHICLE INVESTIGATION SUMMARY**\n\n"
        f"🚗 Vehicle: {vehicle}\n"
        f"👤 Driver: {driver_name}\n"
        f"📍 Location: {location}\n"
        f"⏱️ Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"**Investigation Details:**\n"
        f"• Stop Reason: {stop_reason}\n"
        f"• Mechanic Needed: {'Yes ✓' if needs_mechanic else 'No ✗'}\n"
        f"• Expected Restart: {restart_time}\n"
    )
    
    return summary


def build_unresolved_reason_summary(phone_number: str, reason: str, context: Dict[str, Any]) -> str:
    """Build a summary when issue is not resolved."""
    vehicle = context.get("vehicle_number", "Unknown")
    driver_name = context.get("driver_name", "Driver")
    investigation = context.get("driver_investigation", {})
    
    summary = (
        f"⚠️ **ISSUE NOT RESOLVED**\n\n"
        f"🚗 Vehicle: {vehicle}\n"
        f"👤 Driver: {driver_name}\n"
        f"📋 Reason: {reason}\n\n"
        f"**Previous Investigation:**\n"
        f"• Stop Reason: {investigation.get('stop_reason', 'Unknown').title()}\n"
        f"• Location: {investigation.get('current_location', 'Unknown')}\n"
        f"• Mechanic Required: {'Yes' if investigation.get('needs_mechanic') else 'No'}\n\n"
        f"**Action Required:** Manual intervention needed"
    )
    
    return summary


def save_summary_to_database(phone_number: str, summary: str, context: Dict[str, Any]) -> bool:
    """Save summary to chat messages database."""
    db = SessionLocal()
    try:
        chat = ChatMessage(
            phone_number=phone_number,
            user_message="[INVESTIGATION SUMMARY]",
            bot_response=summary
        )
        db.add(chat)
        db.commit()
        logger.info("Summary saved for %s", phone_number)
        return True
    except Exception as e:
        logger.error("Failed to save summary for %s: %s", phone_number, e, exc_info=True)
        return False
    finally:
        db.close()


def generate_investigation_ai_response(context: Dict[str, Any]) -> str:
    """Generate AI response based on investigation details."""
    investigation = context.get("driver_investigation", {})
    vehicle = context.get("vehicle_number", "Unknown")
    stop_reason = investigation.get("stop_reason", "Unknown")
    location = investigation.get("current_location", "Unknown")
    needs_mechanic = investigation.get("needs_mechanic", False)
    restart_time = investigation.get("expected_restart_time", "Unknown")
    
    prompt = f"""
Based on the following vehicle investigation, provide a brief professional summary and recommendation:

Vehicle: {vehicle}
Stop Reason: {stop_reason.title()}
Current Location: {location}
Mechanic Needed: {'Yes' if needs_mechanic else 'No'}
Expected Restart Time: {restart_time}

Provide:
1. Summary of the situation
2. Recommended actions
3. Follow-up requirements

Keep response brief and in Hinglish (Hindi + English).
"""
    
    try:
        response = generate_ai_answer(prompt)
        return response
    except Exception as e:
        logger.error("Failed to generate AI response: %s", e, exc_info=True)
        return "Unable to generate AI response at this time."


def build_follow_up_message(context: Dict[str, Any]) -> str:
    """Build follow-up message to check if issue is resolved."""
    vehicle = context.get("vehicle_number", "Unknown")
    investigation = context.get("driver_investigation", {})
    restart_time = investigation.get("expected_restart_time", "Unknown")
    
    return (
        f"**FOLLOW-UP CHECK**\n\n"
        f"Vehicle {vehicle}\n"
        f"Expected restart time was: {restart_time}\n\n"
        f"Kya issue ab resolve ho gaya hai?\n"
        f"Reply: Haan / Nahi"
    )


def close_alert_message(context: Dict[str, Any]) -> str:
    """Build final message when alert is closed."""
    vehicle = context.get("vehicle_number", "Unknown")
    driver_name = context.get("driver_name", "Driver")
    investigation = context.get("driver_investigation", {})
    
    message = (
        f"✅ **ALERT CLOSED**\n\n"
        f"🚗 Vehicle: {vehicle}\n"
        f"👤 Driver: {driver_name}\n"
    )
    
    if investigation:
        message += (
            f"📍 Last Location: {investigation.get('current_location', 'Unknown')}\n"
            f"⏱️ Resolved at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    
    message += "\nDhanyavaad support team se contact karne ke liye. 🙏"
    
    return message
