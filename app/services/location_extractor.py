"""
Location Extractor

Extracts location information from natural language input.
Handles:
- Simple locations: "Loni", "Delhi", "Mumbai"
- Movement descriptions: "Loni se Rishikesh ja rahi hai"
- Partial addresses: "Near Metro Station"
- City names: "Kirti Nagar"
"""
import logging
from typing import Optional, Tuple, Dict
from app.ai.groq_llm import generate_response

logger = logging.getLogger("app.location_extractor")


def extract_location_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract location information from natural language text.
    
    Args:
        text: User's message about location
        
    Returns:
        Dictionary with:
        - current_location: Current location of vehicle
        - destination: Destination (if vehicle is moving)
        - is_moving: Boolean indicating if vehicle is in transit
        - raw_text: Original text
    
    Examples:
        "Loni" → {current_location: "Loni", destination: None, is_moving: False}
        "Delhi" → {current_location: "Delhi", destination: None, is_moving: False}
        "Loni se Rishikesh ja rahi hai" → {current_location: "Loni", destination: "Rishikesh", is_moving: True}
        "Near Metro Station" → {current_location: "Near Metro Station", destination: None, is_moving: False}
    """
    try:
        prompt = f"""Extract location information from this text.

User said: "{text}"

Identify:
1. Current location (where vehicle is NOW)
2. Destination (if vehicle is moving/traveling)
3. Is vehicle moving/traveling?

Examples:

Input: "Loni"
Output:
CURRENT: Loni
DESTINATION: None
MOVING: No

Input: "Delhi"
Output:
CURRENT: Delhi
DESTINATION: None
MOVING: No

Input: "Loni se Rishikesh ja rahi hai"
Output:
CURRENT: Loni
DESTINATION: Rishikesh
MOVING: Yes

Input: "Mumbai se Pune ja raha hai"
Output:
CURRENT: Mumbai
DESTINATION: Pune
MOVING: Yes

Input: "Kirti Nagar, Delhi"
Output:
CURRENT: Kirti Nagar, Delhi
DESTINATION: None
MOVING: No

Input: "Near Metro Station"
Output:
CURRENT: Near Metro Station
DESTINATION: None
MOVING: No

Input: "Ghaziabad"
Output:
CURRENT: Ghaziabad
DESTINATION: None
MOVING: No

Respond in EXACTLY this format:
CURRENT: <location>
DESTINATION: <location or None>
MOVING: Yes or No"""

        response = generate_response(prompt).strip()
        
        logger.info(f"Location extraction: '{text[:50]}' -> {response[:100]}")
        
        # Parse LLM response
        lines = response.split('\n')
        current_location = None
        destination = None
        is_moving = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('CURRENT:'):
                current_location = line.replace('CURRENT:', '').strip()
                if current_location.lower() == 'none':
                    current_location = None
            elif line.startswith('DESTINATION:'):
                destination = line.replace('DESTINATION:', '').strip()
                if destination.lower() == 'none':
                    destination = None
            elif line.startswith('MOVING:'):
                moving_str = line.replace('MOVING:', '').strip().lower()
                is_moving = moving_str in ['yes', 'true', 'haan', 'ha']
        
        # If we couldn't extract current location, use the original text
        if not current_location:
            current_location = text.strip()
        
        result = {
            "current_location": current_location,
            "destination": destination,
            "is_moving": is_moving,
            "raw_text": text
        }
        
        logger.info(
            f"Location extracted",
            extra={
                "current": current_location,
                "destination": destination,
                "moving": is_moving
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Location extraction failed: {str(e)}")
        # Fallback: use text as-is
        return {
            "current_location": text.strip(),
            "destination": None,
            "is_moving": False,
            "raw_text": text
        }


def is_valid_location(text: str) -> bool:
    """
    Check if text contains a valid location.
    
    Valid locations:
    - Single words: "Loni", "Delhi", "Mumbai"
    - Multiple words: "Kirti Nagar", "Near Metro Station"
    - Partial addresses: "Ghaziabad", "Rishikesh"
    - Movement descriptions: "Loni se Rishikesh ja rahi hai"
    
    Invalid:
    - Empty or very short: "", "a", "ab"
    - Just numbers: "123"
    - Nonsense: "xyz", "abc"
    """
    normalized = text.strip().lower()
    
    # Must have some content
    if len(normalized) < 2:
        return False
    
    # Check if it's just numbers
    if normalized.isdigit():
        return False
    
    # If it has at least 2 characters, accept it
    # This allows: "Loni", "Delhi", "Mumbai", "Kirti Nagar", "Near Metro", etc.
    return True


def format_location_for_display(location_info: Dict) -> str:
    """
    Format location information for display.
    
    Args:
        location_info: Dictionary from extract_location_info()
        
    Returns:
        Formatted string for display
    """
    current = location_info.get("current_location", "")
    destination = location_info.get("destination")
    is_moving = location_info.get("is_moving", False)
    
    if is_moving and destination:
        return f"{current} → {destination} (Moving)"
    else:
        return current


def format_location_for_storage(location_info: Dict) -> str:
    """
    Format location information for database storage.
    
    Args:
        location_info: Dictionary from extract_location_info()
        
    Returns:
        Formatted string for storage (max 255 chars)
    """
    current = location_info.get("current_location", "")
    destination = location_info.get("destination")
    is_moving = location_info.get("is_moving", False)
    
    if is_moving and destination:
        formatted = f"From: {current}, To: {destination}"
    else:
        formatted = current
    
    # Truncate if too long
    return formatted[:255]
