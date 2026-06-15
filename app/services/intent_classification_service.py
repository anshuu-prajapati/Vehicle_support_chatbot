import logging
import re
from typing import Tuple
from app.ai.groq_llm import generate_response

logger = logging.getLogger("app.intent_classification")

CLASSIFICATION_PROMPT = """You are classifying customer messages about GPS/vehicle issues into specific categories.

Categories (respond with ONLY ONE category name, nothing else):
- WORKSHOP: Vehicle in workshop, repair center, service center, मरम्मत, वर्कशॉप
- ACCIDENT: Vehicle accident, collision, damage, crash, टक्कर, दुर्घटना, एक्सीडेंट
- BATTERY_DISCONNECT: Battery removed, battery disconnected, battery maintenance, बैटरी निकाल, बैटरी हटा
- GPS_REMOVED: GPS removed, GPS detached, GPS निकल गया, GPS हटा दिया
- GPS_DAMAGED: GPS broken, GPS damaged, device damaged, GPS टूट गया, GPS खराब, डिवाइस खराब
- VEHICLE_RUNNING: Vehicle running, driver driving, गाड़ी चल रही है, ड्राइवर चला रहा
- VEHICLE_STANDING: Vehicle parked, driver on leave, vehicle not in use, खड़ी है, पार्क है, छुट्टी
- UNKNOWN: Cannot determine from message or unclear

Customer message in Hindi or English: "{message}"

Respond with ONLY the category name:"""

# Regex patterns for fallback classification (Hindi + English)
INTENT_PATTERNS = {
    "WORKSHOP": [
        r"workshop", r"repair\s*center", r"service\s*center",
        r"मरम्मत", r"वर्कशॉप", r"सर्विस\s*सेंटर", r"रिपेयर"
    ],
    "ACCIDENT": [
        r"accident", r"collision", r"damage", r"crash",
        r"टक्कर", r"दुर्घटना", r"एक्सीडेंट", r"क्षति"
    ],
    "BATTERY_DISCONNECT": [
        r"battery.*remove", r"battery.*disconnect", r"battery.*maintenance",
        r"battery.*nikal", r"बैटरी\s*निकाल", r"बैटरी\s*हटा", r"बैटरी.*मेंटेनेंस"
    ],
    "GPS_REMOVED": [
        r"gps.*nikal", r"gps.*remove", r"gps.*detach", r"gps.*निकल",
        r"gps\s*हटा", r"gps.*khol", r"gps.*खोल"
    ],
    "GPS_DAMAGED": [
        r"gps.*toot", r"gps.*damage", r"gps.*broke", r"device.*damage",
        r"gps\s*टूट", r"gps\s*खराब", r"डिवाइस\s*खराब", r"gps.*kharab"
    ],
    "VEHICLE_RUNNING": [
        r"vehicle.*running", r"driver.*chala", r"gaadi.*chal",
        r"गाड़ी\s*चल\s*रही", r"ड्राइवर.*चला\s*रहा", r"vehicle.*moving",
        r"गाड़ी.*चालू"
    ],
    "VEHICLE_STANDING": [
        r"vehicle.*khadi", r"driver.*leave", r"parked", r"standing",
        r"खड़ी\s*है", r"पार्क\s*है", r"छुट्टी", r"leave.*par",
        r"vehicle.*not.*use", r"vehicle.*idle"
    ],
}


def _regex_classify(message: str) -> str:
    """
    Fallback regex-based classification when LLM fails.
    
    Args:
        message: Customer message to classify
        
    Returns:
        Classification category
    """
    message_lower = message.lower()
    
    # Check each intent pattern
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                logger.info(
                    f"Regex matched: {intent}",
                    extra={"pattern": pattern, "message": message[:100]}
                )
                return intent
    
    logger.info("No regex pattern matched, returning UNKNOWN")
    return "UNKNOWN"


def classify_customer_intent(customer_message: str) -> Tuple[str, str]:
    """
    Classify customer message into issue type using LLM with regex fallback.
    
    Args:
        customer_message: Customer's response about the issue
        
    Returns:
        Tuple of (classification, method) where:
        - classification: One of the 8 issue types or UNKNOWN
        - method: "LLM" or "REGEX" indicating which method was used
        
    Example:
        >>> classify_customer_intent("GPS nikal gaya hai")
        ("GPS_REMOVED", "LLM")
        
        >>> classify_customer_intent("vehicle workshop mein hai")
        ("WORKSHOP", "REGEX")
    """
    # Check for numeric selection first (1-8)
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
    
    normalized = customer_message.strip()
    if normalized in numeric_map:
        logger.info(
            f"Numeric selection: {normalized} -> {numeric_map[normalized]}",
            extra={"message": customer_message, "classification": numeric_map[normalized], "method": "NUMERIC"}
        )
        return numeric_map[normalized], "NUMERIC"
    
    try:
        # Try LLM classification first
        prompt = CLASSIFICATION_PROMPT.format(message=customer_message)
        llm_response = generate_response(prompt).strip().upper()
        
        # Remove any extra text and get just the category
        llm_response = llm_response.split()[0] if llm_response else "UNKNOWN"
        
        # Validate LLM response against known categories
        valid_categories = {
            "WORKSHOP", "ACCIDENT", "BATTERY_DISCONNECT",
            "GPS_REMOVED", "GPS_DAMAGED", "VEHICLE_RUNNING",
            "VEHICLE_STANDING", "UNKNOWN"
        }
        
        if llm_response in valid_categories:
            logger.info(
                f"LLM classified message as: {llm_response}",
                extra={
                    "message": customer_message[:100],
                    "classification": llm_response,
                    "method": "LLM"
                }
            )
            return llm_response, "LLM"
        else:
            logger.warning(
                f"LLM returned invalid category: {llm_response}, falling back to regex",
                extra={
                    "llm_response": llm_response,
                    "message": customer_message[:100]
                }
            )
            
    except Exception as e:
        logger.error(
            f"LLM classification failed: {str(e)}, falling back to regex",
            extra={"error": str(e), "message": customer_message[:100]},
            exc_info=True
        )
    
    # Fallback to regex classification
    regex_result = _regex_classify(customer_message)
    logger.info(
        f"Regex classified message as: {regex_result}",
        extra={
            "message": customer_message[:100],
            "classification": regex_result,
            "method": "REGEX"
        }
    )
    return regex_result, "REGEX"


def get_issue_type_display_name(issue_type: str, language: str = "both") -> str:
    """
    Get display name for issue type in Hindi/English.
    
    Args:
        issue_type: Issue type code
        language: "hindi", "english", or "both"
        
    Returns:
        Display name string
    """
    display_names = {
        "WORKSHOP": {
            "hindi": "वर्कशॉप",
            "english": "Workshop",
            "both": "वर्कशॉप / Workshop"
        },
        "ACCIDENT": {
            "hindi": "दुर्घटना",
            "english": "Accident",
            "both": "दुर्घटना / Accident"
        },
        "BATTERY_DISCONNECT": {
            "hindi": "बैटरी डिस्कनेक्ट",
            "english": "Battery Disconnect",
            "both": "बैटरी डिस्कनेक्ट / Battery Disconnect"
        },
        "GPS_REMOVED": {
            "hindi": "GPS हटा दिया",
            "english": "GPS Removed",
            "both": "GPS हटा दिया / GPS Removed"
        },
        "GPS_DAMAGED": {
            "hindi": "GPS खराब",
            "english": "GPS Damaged",
            "both": "GPS खराब / GPS Damaged"
        },
        "VEHICLE_RUNNING": {
            "hindi": "वाहन चल रहा है",
            "english": "Vehicle Running",
            "both": "वाहन चल रहा है / Vehicle Running"
        },
        "VEHICLE_STANDING": {
            "hindi": "वाहन खड़ा है",
            "english": "Vehicle Standing",
            "both": "वाहन खड़ा है / Vehicle Standing"
        },
        "UNKNOWN": {
            "hindi": "अज्ञात",
            "english": "Unknown",
            "both": "अज्ञात / Unknown"
        }
    }
    
    return display_names.get(issue_type, {}).get(language, issue_type)
