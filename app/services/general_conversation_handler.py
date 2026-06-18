"""
General Conversation Handler

Intercepts and handles general questions, greetings, clarifications, and small talk
BEFORE routing to issue classification flows.

This prevents incorrect routing of questions like:
- "Tum kon ho?" (Who are you?)
- "Kyu message kiya?" (Why did you message?)
- "Kis company se ho?" (Which company?)
- "Kaunsi vehicle?" (Which vehicle?)
- "Hello" / "Thank you" / "Okay"

The handler:
1. Detects general conversation
2. Responds appropriately
3. Maintains conversation state
4. Returns to pending question
"""
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger("app.general_conversation")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def is_general_conversation(text: str) -> bool:
    """
    Check if the message is general conversation (not issue reporting).
    
    Returns True for:
    - Greetings (hello, hi, namaste)
    - Identity questions (who are you, kon ho)
    - Clarifications (why message, what problem, kyu puch rahe ho)
    - Small talk (thank you, okay, achha)
    - Help requests (help me, madad chahiye)
    - Meta questions (kisliye information, kyu information)
    
    Returns False for:
    - Issue descriptions (GPS toot gaya, vehicle workshop mein hai)
    - Status updates (gaadi chal rahi hai, khadi hai)
    - Location responses (Kirti Nagar Delhi, Loni se Rishikesh)
    - Duration responses (2 din se)
    - Confirmation responses (haan service chahiye)
    """
    normalized = _normalize_text(text)
    
    # Quick check for very short acknowledgments
    short_acknowledgments = ["ok", "okay", "k", "hmm", "hm", "achha", "theek", "thik", "yes", "haan", "ji"]
    if normalized in short_acknowledgments:
        return True
    
    # Priority check for general conversation patterns
    # These take precedence over exclusions
    priority_general_patterns = [
        # Identity questions
        "tum kon", "aap kon", "who are you", "kon ho", "kaun ho",
        # Why questions - meta conversation
        "kyu puch", "kyun puch", "kyu pooch", "kyun pooch",
        "kyu message", "kyun message", "why message",
        "kyu call", "kyun call", "why call",
        "kyu sampark", "kyun sampark", "why contact",
        "kisliye", "kis liye", "kyu information", "kyu info",
        # Company/identity
        "kis company", "which company", "konsi company", "kaunsi company",
        # Meta questions
        "kya matlab", "what do you mean", "kya puch rahe",
        "kyu bata", "kyun bata", "why tell",
        # Thanks/greetings
        "thank", "thanks", "dhanyavad", "shukriya",
        "hello", "hi ", "hey ", "namaste", "namaskar",
    ]
    
    for pattern in priority_general_patterns:
        if pattern in normalized:
            return True
    
    # Exclude patterns - these are NOT general conversation
    # Status/location responses
    status_exclude = [
        "workshop", "accident", "battery", "gps", "vehicle", "gaadi",
        "chal rahi", "khadi", "standing", "running", "nikali", "toot",
        "damage", "remove", "service chahiye", "inspection", "repair",
        " se ", " ja rahi", " aa rahi", " ja raha", " aa raha"  # Movement patterns
    ]
    
    # If message contains status keywords and is longer than 2 words, likely not general
    # UNLESS it also has general conversation keywords (already checked above)
    words = normalized.split()
    if len(words) >= 2:
        for exclude in status_exclude:
            if exclude in normalized:
                return False
    
    # Vehicle clarification questions (not status)
    vehicle_patterns = [
        "kaunsi vehicle", "konsi vehicle", "which vehicle", "kis vehicle ki baat",
        "kaunsi gaadi", "konsi gaadi", "which gaadi", "vehicle number kya"
    ]
    
    # Problem clarification (asking what the problem is, not describing it)
    problem_patterns = [
        "kya hua hai", "kya problem hai", "kya issue hai", "what happened",
        "kya samasya hai", "kaunsi problem", "konsi problem", "kya galat"
    ]
    
    # Understanding/confusion
    confusion_patterns = [
        "samajh nahi aaya", "samajh nahi aa raha", "understand nahi hua",
        "clear nahi", "confused hun"
    ]
    
    # Automated/bot questions
    automated_patterns = [
        "automated hai", "bot hai", "robot hai", "automatic hai", "machine hai",
        "computer hai", "real person", "insaan ho"
    ]
    
    # Help requests
    help_patterns = [
        "help me", "help kar", "madad kar", "madad chahiye",
        "sahayata chahiye", "kya karu main"
    ]
    
    # Check remaining patterns
    remaining_patterns = (
        vehicle_patterns + problem_patterns + confusion_patterns +
        automated_patterns + help_patterns
    )
    
    for pattern in remaining_patterns:
        if pattern in normalized:
            return True
    
    return False


def get_conversation_type(text: str) -> str:
    """
    Classify the type of general conversation.
    
    Returns:
    - IDENTITY: Who are you?
    - WHY_CONTACT: Why did you message?
    - COMPANY: Which company?
    - VEHICLE: Which vehicle?
    - PROBLEM: What's the problem?
    - CONFUSION: I don't understand
    - AUTOMATED: Is this automated?
    - GREETING: Hello/Hi
    - THANKS: Thank you
    - HELP: Help me
    - ACKNOWLEDGMENT: Ok/Achha
    - GENERAL: Other general conversation
    """
    normalized = _normalize_text(text)
    
    # Short acknowledgments
    if normalized in ["ok", "okay", "k", "hmm", "hm", "achha", "theek", "thik", "yes", "haan", "ji"]:
        return "ACKNOWLEDGMENT"
    
    # Identity
    if any(p in normalized for p in ["tum kon", "aap kon", "who are you", "kon ho", "kaun ho", "naam kya", "your name", "kon bol", "kaun bol"]):
        return "IDENTITY"
    
    # Why contact - broader patterns
    if any(p in normalized for p in ["kyu message", "kyun message", "why message", "kyu call", "kyu sampark", "kyu bola", "kyu puch", "kyun puch", "kyu pooch", "kyun pooch", "kisliye", "kis liye", "kyu information", "kyu bata"]):
        return "WHY_CONTACT"
    
    # Company
    if any(p in normalized for p in ["kis company", "which company", "konsi company", "kaunsi company", "company ka naam"]):
        return "COMPANY"
    
    # Vehicle
    if any(p in normalized for p in ["kaunsi vehicle", "konsi vehicle", "which vehicle", "kis vehicle", "kaunsi gaadi", "konsi gaadi"]):
        return "VEHICLE"
    
    # Problem
    if any(p in normalized for p in ["kya hua", "kya problem", "kya issue", "what happened", "what problem", "kya samasya", "kaunsi problem"]):
        return "PROBLEM"
    
    # Confusion
    if any(p in normalized for p in ["samajh nahi", "understand nahi", "clear nahi", "kya matlab", "confused"]):
        return "CONFUSION"
    
    # Automated
    if any(p in normalized for p in ["automated", "bot hai", "robot hai", "automatic", "machine hai", "computer hai", "real person"]):
        return "AUTOMATED"
    
    # Greeting
    if any(p in normalized for p in ["hello", "hi", "hey", "namaste", "namaskar", "good morning", "good afternoon", "good evening"]):
        return "GREETING"
    
    # Thanks
    if any(p in normalized for p in ["thank", "thanks", "dhanyavad", "shukriya"]):
        return "THANKS"
    
    # Help
    if any(p in normalized for p in ["help", "madad", "sahayata", "kya karu", "batao", "samjhao"]):
        return "HELP"
    
    return "GENERAL"


def generate_general_response(
    conversation_type: str,
    vehicle_number: Optional[str] = None,
    last_location: Optional[str] = None,
    pending_question: Optional[str] = None
) -> str:
    """
    Generate appropriate response for general conversation.
    
    Args:
        conversation_type: Type of conversation
        vehicle_number: Vehicle number if available
        last_location: Last known location if available
        pending_question: Current pending question to return to
        
    Returns:
        Response message
    """
    
    if conversation_type == "IDENTITY":
        response = "Main GPS Support Assistant hoon. 😊\n\n"
        if vehicle_number:
            response += f"Humein vehicle {vehicle_number} se GPS data receive nahi ho raha hai, isliye hum issue samajhne ki koshish kar rahe hain.\n\n"
        else:
            response += "Main aapki vehicle ke GPS issue samajhne mein madad karta hoon.\n\n"
    
    elif conversation_type == "WHY_CONTACT":
        response = ""
        if vehicle_number:
            response += f"Vehicle {vehicle_number} se GPS data receive nahi ho raha hai.\n\n"
            if last_location:
                response += f"Last known location: {last_location}\n\n"
        else:
            response += "Aapki vehicle se GPS data receive nahi ho raha hai.\n\n"
        response += "Hum issue ka reason samajhna chahte hain taaki sahi solution provide kar sakein.\n\n"
    
    elif conversation_type == "COMPANY":
        response = "Main GPS tracking system ki support team ki taraf se hoon.\n\n"
        response += "Hum aapki vehicle ke GPS issue resolve karne mein madad kar rahe hain.\n\n"
    
    elif conversation_type == "VEHICLE":
        if vehicle_number:
            response = f"Hum vehicle number *{vehicle_number}* ke baare mein baat kar rahe hain.\n\n"
            if last_location:
                response += f"Last known location: {last_location}\n\n"
        else:
            response = "Hum aapki registered vehicle ke baare mein baat kar rahe hain.\n\n"
    
    elif conversation_type == "PROBLEM":
        response = "Vehicle se GPS data receive nahi ho raha hai.\n\n"
        response += "Hum issue ka sahi reason jaanna chahte hain (jaise vehicle workshop mein hai, GPS damage hai, etc.) taaki hum sahi solution provide kar sakein.\n\n"
    
    elif conversation_type == "CONFUSION":
        response = "Koi baat nahi. 😊\n\n"
        response += "Hum sirf yeh jaanna chahte hain ki vehicle ki current status kya hai taaki GPS issue solve kar sakein.\n\n"
    
    elif conversation_type == "AUTOMATED":
        response = "Haan, main GPS Support Assistant hoon aur vehicle se sambandhit samasya samajhne mein madad karta hoon. 😊\n\n"
    
    elif conversation_type == "GREETING":
        response = "Namaste Sir 👋\n\n"
        response += "Main GPS Support Assistant hoon.\n\n"
    
    elif conversation_type == "THANKS":
        response = "Aapka swagat hai. 😊\n\n"
    
    elif conversation_type == "HELP":
        response = "Main aapki madad karne ke liye yahan hoon. 😊\n\n"
        response += "Kripya vehicle ki current status ke baare mein bataiye taaki hum GPS issue solve kar sakein.\n\n"
    
    elif conversation_type == "ACKNOWLEDGMENT":
        response = "Dhanyavaad. 😊\n\n"
    
    else:  # GENERAL
        response = "Samajh gaya. 😊\n\n"
    
    # Add pending question if provided
    if pending_question:
        response += pending_question
    
    return response.strip()


def get_pending_question(current_step: str, context: dict = None) -> Optional[str]:
    """
    Get the pending question based on current conversation step.
    
    Args:
        current_step: Current conversation step
        context: Current conversation context
        
    Returns:
        Pending question to ask user
    """
    from app.services.state_manager import ConversationStep
    
    # Initial selection
    if not current_step or current_step == ConversationStep.MAIN_MENU.value:
        return "Kripya batayein ki vehicle ki current status kya hai?"
    
    # GPS Damaged location
    if current_step == ConversationStep.GPS_DAMAGED_LOCATION.value:
        sub_step = context.get("gps_damaged_sub_step") if context else None
        if sub_step == "GPS_DAMAGED_LOCATION" or not sub_step:
            return "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai."
        elif sub_step == "GPS_DAMAGED_VISIT_DATETIME":
            return "Vehicle inspection ke liye kab available rahegi?"
        elif sub_step == "GPS_DAMAGED_CONTACT_CONFIRM":
            return "Kis number par aapse contact karna hai?"
    
    # Vehicle Running location
    if current_step == ConversationStep.VEHICLE_RUNNING_DRIVER_NAME.value:
        return "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai."
    
    # Vehicle Standing duration
    if current_step == ConversationStep.VEHICLE_STANDING_DURATION.value:
        return "Vehicle kab se standing condition mein hai?"
    
    # Workshop expected date
    if current_step == ConversationStep.WORKSHOP_CONFIRMATION.value:
        return "Vehicle ke dobara operational hone ki expected date kya hai?"
    
    # Battery expected date
    if current_step == ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION.value:
        return "Vehicle ya battery system dobara kab operational hoga?"
    
    # GPS Removed reinstallation date
    if current_step == ConversationStep.GPS_REMOVED_REINSTALL_DATE.value:
        return "GPS re-installation kab karwana hai?"
    
    # Accident workshop confirmation
    if current_step == ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION.value:
        return "Kya vehicle filhaal workshop ya repair center mein hai?"
    
    # Other issue description
    if current_step == ConversationStep.OTHER_ISSUE_DESCRIPTION.value:
        return "Vehicle ya GPS ke saath kya issue aa raha hai?"
    
    # Default fallback
    return "Kripya apna response dein."


def handle_general_conversation(
    text: str,
    current_step: str,
    context: dict = None,
    vehicle_number: Optional[str] = None,
    last_location: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if message is general conversation and handle it.
    
    Args:
        text: User's message
        current_step: Current conversation step
        context: Current conversation context
        vehicle_number: Vehicle number if available
        last_location: Last known location if available
        
    Returns:
        Tuple of (is_general_conversation, response_message)
        - If is_general_conversation is True, response_message contains the reply
        - If is_general_conversation is False, response_message is None
    """
    
    if not is_general_conversation(text):
        return False, None
    
    logger.info(
        f"General conversation detected: '{text[:50]}'",
        extra={"text": text[:100]}
    )
    
    # Get conversation type
    conv_type = get_conversation_type(text)
    
    logger.info(
        f"Conversation type: {conv_type}",
        extra={"type": conv_type}
    )
    
    # Get pending question
    pending_question = get_pending_question(current_step, context)
    
    # Generate response
    response = generate_general_response(
        conv_type,
        vehicle_number=vehicle_number,
        last_location=last_location,
        pending_question=pending_question
    )
    
    return True, response
