"""
Fallback Handler Service

Provides LLM-based fallback when user response is unclear or unexpected.
Ensures conversation never breaks by intelligently interpreting user intent.
"""
import logging
from typing import Tuple, Optional
from app.ai.groq_llm import generate_response

logger = logging.getLogger("app.fallback_handler")


def analyze_user_intent_with_llm(
    user_message: str,
    context: str,
    expected_response_type: str
) -> Tuple[bool, Optional[str], str]:
    """
    Use LLM to understand unclear user responses.
    
    Args:
        user_message: The user's unclear message
        context: What question was asked (context)
        expected_response_type: What type of response we expect (yes/no, date, time, etc.)
        
    Returns:
        Tuple of (understood, extracted_value, explanation)
    """
    try:
        prompt = f"""You are a helpful assistant analyzing customer responses in a GPS service chatbot.

Context: We asked the customer: "{context}"
Expected Response Type: {expected_response_type}
Customer's Response: "{user_message}"

Your task: Determine if the customer's response answers the question, even if not in the expected format.

Response Types:
- yes_no: Customer should say yes/no (haan/nahi)
- date: Customer should provide a date
- time: Customer should provide a time
- location: Customer should provide a location/address
- phone: Customer should provide a phone number
- text: Free text response

Analyze the customer's response and respond in this exact format:
UNDERSTOOD: yes or no
VALUE: <extracted value if understood, or NONE>
EXPLANATION: <brief explanation in Hindi and English>

Examples:
Input: "4 ghante se" for "How long has vehicle been standing?" expecting duration
Output:
UNDERSTOOD: yes
VALUE: less than 24 hours
EXPLANATION: Customer said 4 hours, which is less than 24 hours / ग्राहक ने 4 घंटे कहा, जो 24 घंटे से कम है

Input: "kal subah" for "When is vehicle available?" expecting date
Output:
UNDERSTOOD: yes
VALUE: tomorrow morning
EXPLANATION: Customer said tomorrow morning / ग्राहक ने कल सुबह कहा

Input: "xyz" for "Is vehicle in workshop?" expecting yes/no
Output:
UNDERSTOOD: no
VALUE: NONE
EXPLANATION: Response is unclear, please answer yes or no / जवाब स्पष्ट नहीं है, कृपया हाँ या नहीं में उत्तर दें

Now analyze this:"""
        
        response = generate_response(prompt)
        
        # Parse LLM response
        lines = response.strip().split('\n')
        understood = False
        value = None
        explanation = ""
        
        for line in lines:
            if line.startswith('UNDERSTOOD:'):
                understood = 'yes' in line.lower()
            elif line.startswith('VALUE:'):
                value_part = line.split(':', 1)[1].strip()
                value = None if value_part == 'NONE' else value_part
            elif line.startswith('EXPLANATION:'):
                explanation = line.split(':', 1)[1].strip()
        
        logger.info(
            f"LLM Fallback Analysis",
            extra={
                "user_message": user_message[:50],
                "understood": understood,
                "value": value,
                "explanation": explanation[:100]
            }
        )
        
        return understood, value, explanation
        
    except Exception as e:
        logger.error(f"LLM fallback analysis failed: {str(e)}", exc_info=True)
        return False, None, "कुछ गलत हो गया। कृपया फिर से प्रयास करें। / Something went wrong. Please try again."


def create_clarification_message(
    original_question: str,
    expected_format: str,
    llm_explanation: str = None
) -> str:
    """
    Create a helpful clarification message when user response is unclear.
    
    Args:
        original_question: The question we asked
        expected_format: Format we expect (e.g., "DD/MM/YYYY", "yes/no")
        llm_explanation: Optional explanation from LLM
        
    Returns:
        Clarification message in Hindi and English
    """
    base_message = "⚠️ आपका जवाब स्पष्ट नहीं था।\n⚠️ Your response was not clear.\n\n"
    
    if llm_explanation:
        base_message += f"{llm_explanation}\n\n"
    
    base_message += f"{original_question}\n\n"
    
    if expected_format:
        base_message += f"कृपया इस फॉर्मेट में जवाब दें: {expected_format}\n"
        base_message += f"Please respond in this format: {expected_format}"
    
    return base_message


def handle_unexpected_response(
    user_message: str,
    current_question: str,
    expected_type: str,
    valid_options: list = None
) -> Tuple[bool, Optional[str], str]:
    """
    Handle unexpected user responses with LLM fallback.
    
    Args:
        user_message: User's message
        current_question: Question we asked
        expected_type: Type of response expected
        valid_options: List of valid options if applicable
        
    Returns:
        Tuple of (is_valid, extracted_value, response_message)
    """
    # First, try LLM analysis
    understood, value, explanation = analyze_user_intent_with_llm(
        user_message,
        current_question,
        expected_type
    )
    
    if understood and value:
        # LLM understood the intent
        logger.info(
            f"LLM successfully interpreted unclear response",
            extra={
                "original": user_message[:50],
                "interpreted": value,
                "type": expected_type
            }
        )
        return True, value, None  # No error message needed
    
    # LLM couldn't understand - create helpful clarification
    options_text = ""
    if valid_options:
        options_text = "\n\nवैध विकल्प / Valid options:\n" + "\n".join(valid_options)
    
    clarification = create_clarification_message(
        current_question,
        expected_type,
        explanation if explanation else None
    )
    
    if options_text:
        clarification += options_text
    
    return False, None, clarification


def wrap_flow_handler_with_fallback(handler_function):
    """
    Decorator to wrap flow handlers with LLM fallback.
    
    Usage:
        @wrap_flow_handler_with_fallback
        def handle_my_flow(...):
            ...
    """
    def wrapper(*args, **kwargs):
        try:
            return handler_function(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Flow handler error in {handler_function.__name__}: {str(e)}",
                exc_info=True
            )
            
            # Never break - always return a helpful message
            return (
                "⚠️ कुछ गलत हो गया।\n"
                "⚠️ Something went wrong.\n\n"
                "कृपया अपना जवाब फिर से भेजें।\n"
                "Please send your response again.\n\n"
                "या 'शुरू से' टाइप करें नई शुरुआत के लिए।\n"
                "Or type 'reset' to start fresh."
            )
    
    return wrapper


def should_reset_conversation(user_message: str) -> bool:
    """
    Check if user wants to reset/restart conversation.
    
    Args:
        user_message: User's message
        
    Returns:
        True if user wants to reset
    """
    reset_keywords = [
        "reset", "restart", "start again", "शुरू से", "shuru se",
        "naya", "new", "dobara", "फिर से", "phir se"
    ]
    
    normalized = user_message.strip().lower()
    return any(keyword in normalized for keyword in reset_keywords)
