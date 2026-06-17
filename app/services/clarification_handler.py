"""
Global Clarification and Conversation Recovery Handler

This module provides global logic to detect when users are confused,
asking questions, or need help, and provides appropriate responses
WITHOUT advancing the workflow.
"""
import logging
from typing import Tuple, Optional

logger = logging.getLogger("app.clarification_handler")


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.strip().lower() if text else ""


def detect_user_intent(user_message: str) -> str:
    """
    Detect if user is answering, asking a question, confused, or needs help.
    
    Returns:
        - "ANSWER" - User is providing an answer
        - "QUESTION" - User is asking a question
        - "CONFUSION" - User is confused
        - "HELP_REQUEST" - User needs help/explanation
        - "OFF_TOPIC" - User is going off-topic
    """
    from app.ai.groq_llm import generate_response
    
    normalized = _normalize_text(user_message)
    
    # Quick checks for obvious confusion/question patterns
    confusion_keywords = [
        "samajh nahi", "samajh nahi aaya", "samajh nahi paya", "samjha nahi",
        "kya matlab", "matlab", "kya ka matlab", 
        "clear nahi", "clear nahi hai", "clear nahi ho raha",
        "confused", "confusion", "understand nahi",
        "pata nahi", "nahi pata", "nahi samajh aaya"
    ]
    
    question_keywords = [
        "kyun", "kyu", "why", "kaise", "how", "kab", "when",
        "kaha", "where", "kya hai", "what is", "batao", "bata do",
        "explain", "bataye", "bataiye", "samjhao", "samjhaiye",
        "detail", "thoda aur", "aur batao"
    ]
    
    help_keywords = [
        "help", "madad", "sahayata", "batao kya karna hai",
        "kya karu", "aage kya", "next kya"
    ]
    
    # Check for confusion
    if any(keyword in normalized for keyword in confusion_keywords):
        logger.info(f"Quick detect: CONFUSION - '{user_message[:50]}'")
        return "CONFUSION"
    
    # Check for questions
    if any(keyword in normalized for keyword in question_keywords):
        logger.info(f"Quick detect: QUESTION - '{user_message[:50]}'")
        return "QUESTION"
    
    # Check for help requests
    if any(keyword in normalized for keyword in help_keywords):
        logger.info(f"Quick detect: HELP_REQUEST - '{user_message[:50]}'")
        return "HELP_REQUEST"
    
    # Use LLM for semantic understanding
    try:
        prompt = f"""Classify user's intent in a conversation with a chatbot.

User's message: "{user_message}"

Intents:
1. ANSWER - User is providing a direct answer (location, date, yes/no, etc.)
2. QUESTION - User is asking a question about something
3. CONFUSION - User is confused or doesn't understand
4. HELP_REQUEST - User is asking for help or explanation

Examples:

ANSWER:
- "Haan"
- "Kirti Nagar, Delhi"
- "20-06-2026"
- "Kal subah"
- "Nahi"

QUESTION:
- "Kyun pooch rahe ho?"
- "Ye kya hai?"
- "Kaise?"
- "Kab tak lagega?"

CONFUSION:
- "Mujhe samajh nahi aaya"
- "Kya matlab?"
- "Clear nahi hai"
- "Confused hoon"

HELP_REQUEST:
- "Batao kya karna hai"
- "Help chahiye"
- "Explain karo"
- "Thoda aur batao"

Respond with ONLY ONE WORD: ANSWER, QUESTION, CONFUSION, or HELP_REQUEST"""

        response = generate_response(prompt).strip().upper()
        
        logger.info(f"LLM intent detection: '{user_message[:50]}' -> {response}")
        
        # Validate response
        valid_intents = ["ANSWER", "QUESTION", "CONFUSION", "HELP_REQUEST", "OFF_TOPIC"]
        if response in valid_intents:
            return response
        
        # Default to ANSWER if unclear
        return "ANSWER"
        
    except Exception as e:
        logger.error(f"LLM intent detection failed: {str(e)}")
        # Default to ANSWER to avoid blocking workflow
        return "ANSWER"


def should_clarify(user_message: str) -> bool:
    """
    Check if we should provide clarification instead of processing as answer.
    
    Returns:
        True if user needs clarification (don't advance workflow)
        False if user is providing answer (continue workflow)
    """
    intent = detect_user_intent(user_message)
    
    # If user is confused, asking question, or needs help - clarify
    if intent in ["QUESTION", "CONFUSION", "HELP_REQUEST"]:
        logger.info(f"Clarification needed - Intent: {intent}")
        return True
    
    # Otherwise, treat as answer and continue
    logger.info(f"Processing as answer - Intent: {intent}")
    return False


def generate_clarification_response(
    user_message: str,
    current_question: str,
    context_explanation: str
) -> str:
    """
    Generate a helpful clarification response.
    
    Args:
        user_message: What user said
        current_question: The question bot asked
        context_explanation: Why we're asking this question
        
    Returns:
        Clarification message
    """
    from app.ai.groq_llm import generate_response
    
    intent = detect_user_intent(user_message)
    
    try:
        prompt = f"""User is confused or asking a question. Generate a helpful clarification response.

Current Question: "{current_question}"

Context: {context_explanation}

User's Response: "{user_message}"

User's Intent: {intent}

Generate a response that:
1. Acknowledges user's confusion/question
2. Explains the current question in simple language
3. Provides context about why we're asking
4. Re-asks the same question
5. Keeps it friendly and conversational in Hindi/Hinglish

Format:
Koi baat nahi. 😊

[Simple explanation of what we're asking and why]

[Re-ask the question]

Example:
Koi baat nahi. 😊

Mera matlab hai: Hum GPS device ko dobara lagwane ke liye service engineer arrange kar sakte hain.

Kya aap GPS installation ki process aage badhana chahte hain?"""

        clarification = generate_response(prompt).strip()
        
        logger.info(f"Generated clarification for intent: {intent}")
        
        return clarification
        
    except Exception as e:
        logger.error(f"Clarification generation failed: {str(e)}")
        
        # Fallback response
        return (
            f"Koi baat nahi. 😊\n\n"
            f"{context_explanation}\n\n"
            f"{current_question}"
        )


def get_context_explanation_for_step(step: str, sub_step: str = None) -> str:
    """
    Get context explanation for a specific conversation step.
    
    This helps explain WHY we're asking each question.
    """
    explanations = {
        # GPS Damaged Flow
        "GPS_DAMAGED_LOCATION": {
            "GPS_DAMAGED_CONFIRMATION": "Hum pooch rahe hain ki aap GPS installation ke liye abhi service chahte hain ya baad mein. Agar abhi chahte hain to hum service engineer arrange kar denge.",
            "GPS_DAMAGED_EXPECTED_DATE": "Hum pooch rahe hain ki GPS kab tak operational ho jayega taaki hum aapko us date par dobara contact kar sakein.",
            "GPS_DAMAGED_LOCATION": "Hum vehicle ki location isliye pooch rahe hain taaki service engineer ko pata rahe kahan aana hai inspection ke liye.",
            "GPS_DAMAGED_VISIT_DATETIME": "Hum pooch rahe hain ki vehicle kab available rahegi taaki service engineer ki visit schedule kar sakein.",
            "GPS_DAMAGED_CONTACT_CONFIRM": "Hum confirm kar rahe hain ki kis number par aapse contact karna hai service engineer ke visit ke liye.",
            "GPS_DAMAGED_ADDITIONAL_INFO": "Agar aapko koi additional information share karni hai (jaise GPS ka condition, landmarks, etc.) to bata sakte hain. Ye optional hai."
        },
        
        # Vehicle Running Flow
        "VEHICLE_RUNNING_DRIVER_NAME": {
            "VR_LOCATION": "Hum vehicle ki current location isliye pooch rahe hain taaki service engineer ko pata rahe kahan aana hai GPS check karne ke liye.",
            "VR_VISIT_DATETIME": "Hum pooch rahe hain ki inspection ke liye vehicle kab available rahegi taaki service engineer ki visit schedule kar sakein.",
            "VR_CONTACT_CONFIRM": "Hum confirm kar rahe hain ki kis number par aapse contact karna hai service engineer ke visit ke liye.",
            "VR_ADDITIONAL_INFO": "Agar driver ka naam ya koi additional information share karni hai to bata sakte hain. Ye optional hai."
        },
        
        # GPS Removed Flow
        "GPS_REMOVED_REINSTALL_DATE": {
            "GPS_REMOVED_EXPECTED_DATE": "Hum pooch rahe hain ki GPS kab tak dobara operational ho jayega taaki hum record mein note kar sakein.",
            "GPS_REMOVED_INSTALLATION_DATE": "Hum pooch rahe hain ki GPS reinstallation kab karwana hai taaki service engineer ki visit schedule kar sakein.",
            "GPS_REMOVED_LOCATION": "Hum vehicle ki location pooch rahe hain taaki service engineer ko pata rahe kahan GPS installation karna hai.",
            "GPS_REMOVED_CONTACT_CONFIRM": "Hum confirm kar rahe hain ki kis number par aapse contact karna hai GPS installation ke liye.",
            "GPS_REMOVED_AVAILABILITY_DATE": "Hum pooch rahe hain ki vehicle kab available rahegi GPS installation ke liye.",
            "GPS_REMOVED_ADDITIONAL_INFO": "Agar installation ke baare mein koi additional information share karni hai to bata sakte hain. Ye optional hai."
        },
        
        # Workshop Flow
        "WORKSHOP_CONFIRMATION": {
            None: "Hum pooch rahe hain ki vehicle filhaal workshop mein hai ya nahi, taaki hum samajh sakein ki service engineer ki zarurat hai ya nahi."
        },
        
        # Accident Flow
        "ACCIDENT_WORKSHOP_CONFIRMATION": {
            None: "Hum pooch rahe hain ki accident ke baad vehicle workshop mein hai ya nahi, taaki hum aage ki process decide kar sakein."
        },
        
        # Battery Flow
        "BATTERY_MAINTENANCE_CONFIRMATION": {
            None: "Hum pooch rahe hain ki battery maintenance ke liye disconnect ki gayi hai ya nahi, taaki hum samajh sakein ki issue kya hai."
        }
    }
    
    # Get explanation for current step
    step_explanations = explanations.get(step, {})
    
    if sub_step and sub_step in step_explanations:
        return step_explanations[sub_step]
    elif None in step_explanations:
        return step_explanations[None]
    else:
        return "Hum aapki madad karne ke liye ye information collect kar rahe hain."


def get_current_question_text(step: str, sub_step: str = None) -> str:
    """
    Get the text of the current question being asked.
    """
    questions = {
        # GPS Damaged Flow
        "GPS_DAMAGED_LOCATION": {
            "GPS_DAMAGED_CONFIRMATION": "Kya aap GPS installation ke liye service request continue karna chahte hain?",
            "GPS_DAMAGED_EXPECTED_DATE": "GPS kab tak running ho jayega ya installation complete ho jayega?",
            "GPS_DAMAGED_LOCATION": "Vehicle ki current location kya hai jahan inspection karwana hai?",
            "GPS_DAMAGED_VISIT_DATETIME": "Vehicle inspection ke liye kab available rahegi?",
            "GPS_DAMAGED_CONTACT_CONFIRM": "Kis number par aapse contact karna hai?",
            "GPS_DAMAGED_ADDITIONAL_INFO": "Koi additional information share karna chahte hain?"
        },
        
        # Vehicle Running Flow
        "VEHICLE_RUNNING_DRIVER_NAME": {
            "VR_LOCATION": "Vehicle ki current location kya hai?",
            "VR_VISIT_DATETIME": "Vehicle inspection ke liye kab available rahegi?",
            "VR_CONTACT_CONFIRM": "Kis number par aapse contact karna hai?",
            "VR_ADDITIONAL_INFO": "Koi additional information share karna chahte hain?"
        },
        
        # GPS Removed Flow
        "GPS_REMOVED_REINSTALL_DATE": {
            "GPS_REMOVED_EXPECTED_DATE": "GPS kab tak dobara operational ho jayega?",
            "GPS_REMOVED_INSTALLATION_DATE": "GPS reinstallation kab karwana hai?",
            "GPS_REMOVED_LOCATION": "Vehicle ki current location kya hai?",
            "GPS_REMOVED_CONTACT_CONFIRM": "Kis number par aapse contact karna hai?",
            "GPS_REMOVED_AVAILABILITY_DATE": "Vehicle kab available rahegi GPS installation ke liye?",
            "GPS_REMOVED_ADDITIONAL_INFO": "Koi additional information share karna chahte hain?"
        }
    }
    
    step_questions = questions.get(step, {})
    
    if sub_step and sub_step in step_questions:
        return step_questions[sub_step]
    elif None in step_questions:
        return step_questions[None]
    else:
        return "Kripya apna response dein."
