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
        "next_state": ConversationStep.VEHICLE_NUMBER,
        "issue_type": "vehicle_problem",
        "ask_text": (
            "Kripya vehicle number bataye.\n"
            "Example:\n"
            "DL01AB1234"
        ),
    },
    MenuAction.ENGINEER_REQUEST: {
        "next_state": ConversationStep.ASK_DRIVER_AVAILABILITY,
        "issue_type": "engineer_request",
        "ask_text": (
            "Kya driver vehicle ke paas hai?\n"
            "1️⃣ Haan\n"
            "2️⃣ Nahi"
        ),
    },
}

CONVERSATION_STATES = [step.value for step in ConversationStep]
