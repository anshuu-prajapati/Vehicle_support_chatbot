from enum import Enum

from app.services.state_manager import ConversationStep


class MenuAction(str, Enum):
    VEHICLE_PROBLEM = "VEHICLE_PROBLEM"
    ENGINEER_REQUEST = "ENGINEER_REQUEST"


GREETING_KEYWORDS = [
    "hi",
    "hii",
    "hello",
    "hey",
    "namaste",
    "good morning",
    "good afternoon",
    "good evening",
]

MENU_OPTIONS = {
    "1": MenuAction.VEHICLE_PROBLEM,
    "one": MenuAction.VEHICLE_PROBLEM,
    "vehicle problem": MenuAction.VEHICLE_PROBLEM,
    "problem": MenuAction.VEHICLE_PROBLEM,
    "2": MenuAction.ENGINEER_REQUEST,
    "two": MenuAction.ENGINEER_REQUEST,
    "engineer": MenuAction.ENGINEER_REQUEST,
    "engineer chahiye": MenuAction.ENGINEER_REQUEST,
    "engineer request": MenuAction.ENGINEER_REQUEST,
}

MENU_TEXT = (
    "Aapko kis tarah ki madad chahiye?\n"
    "\n"
    "1️⃣ Vehicle Problem\n"
    "\n"
    "2️⃣ Engineer Chahiye\n"
    "\n"
    "Reply with 1 or 2."
)

INVALID_MENU_SELECTION_RESPONSE = (
    "Kripya valid option select kare.\n"
    "\n"
    "1️⃣ Vehicle Problem\n"
    "\n"
    "2️⃣ Engineer Chahiye"
)

MENU_CHOICES = {
    MenuAction.VEHICLE_PROBLEM: {
        "next_state": ConversationStep.ASK_RIGHT_PERSON,
        "issue_type": "vehicle_problem",
        "ask_text": (
            # This will be dynamically replaced with company name in menu_service.py
            "क्या हम {company_name} के मैनेजर से बात कर रहे हैं?\n"
            "Are we talking to the manager of {company_name}?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        ),
    },
    MenuAction.ENGINEER_REQUEST: {
        "next_state": ConversationStep.ASK_RIGHT_PERSON,
        "issue_type": "engineer_request",
        "ask_text": (
            # This will be dynamically replaced with company name in menu_service.py
            "क्या हम {company_name} के मैनेजर से बात कर रहे हैं?\n"
            "Are we talking to the manager of {company_name}?\n\n"
            "1️⃣ हाँ / Yes\n"
            "2️⃣ नहीं / No"
        ),
    },
}

CONVERSATION_STATES = [step.value for step in ConversationStep]
