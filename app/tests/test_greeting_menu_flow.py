import unittest
from unittest.mock import MagicMock

from app.services.greeting_service import GreetingService
from app.services.menu_service import MenuService
from app.services.state_manager import ConversationStep, StateManager
from app.services.support_flow_service import handle_support_message


class DummyState:
    def __init__(self, phone_number, current_step, context_json=None):
        self.phone_number = phone_number
        self.current_step = current_step
        self.context_json = context_json or {}


class DummyRepository:
    def __init__(self):
        self.states = {}

    def get_by_phone(self, phone_number):
        return self.states.get(phone_number)

    def get_by_phone_for_update(self, phone_number):
        return self.states.get(phone_number)

    def create(self, phone_number, current_step, context_json=None):
        state = DummyState(phone_number, current_step, context_json or {})
        self.states[phone_number] = state
        return state

    def update(self, state, current_step=None, context_json=None):
        if current_step is not None:
            state.current_step = current_step
        if context_json is not None:
            state.context_json = context_json
        return state

    def delete_by_phone(self, phone_number):
        return self.states.pop(phone_number, None) is not None


class DummyUser:
    def __init__(self, phone_number, name=None, user_id=1):
        self.phone_number = phone_number
        self.name = name
        self.id = user_id


class GreetingMenuFlowTests(unittest.TestCase):
    def setUp(self):
        self.repository = DummyRepository()
        self.state_manager = StateManager(db=MagicMock(), repository=self.repository)
        self.user = DummyUser(phone_number="+911234567890", name="Anita")

    def test_greeting_service_detects_greeting(self):
        service = GreetingService(self.state_manager)

        self.assertTrue(service.is_greeting("Hello"))
        self.assertTrue(service.is_greeting("good evening"))
        self.assertFalse(service.is_greeting("where is the vehicle"))

    def test_greeting_service_resets_state_and_returns_menu(self):
        service = GreetingService(self.state_manager)
        self.repository.create(self.user.phone_number, ConversationStep.ASK_LOCATION.value)

        service.route_to_main_menu(self.user.phone_number)
        self.assertEqual(self.repository.states[self.user.phone_number].current_step, ConversationStep.MAIN_MENU.value)

        welcome_text = service.send_welcome(self.user.name)
        self.assertIn("Namaste Anita Ji", welcome_text)
        self.assertIn("1️⃣ Vehicle Problem", welcome_text)
        self.assertIn("2️⃣ Engineer Chahiye", welcome_text)

    def test_menu_service_vehicle_problem_selection(self):
        service = MenuService(self.state_manager)

        result = service.handle_menu_selection(self.user.phone_number, "1")

        state = self.repository.states[self.user.phone_number]
        self.assertEqual(state.current_step, ConversationStep.VEHICLE_NUMBER.value)
        self.assertEqual(state.context_json["issue_type"], "vehicle_problem")
        self.assertIn("Kripya vehicle number bataye", result)

    def test_menu_service_engineer_request_selection(self):
        service = MenuService(self.state_manager)

        result = service.handle_menu_selection(self.user.phone_number, "engineer chahiye")

        state = self.repository.states[self.user.phone_number]
        self.assertEqual(state.current_step, ConversationStep.ASK_DRIVER_AVAILABILITY.value)
        self.assertEqual(state.context_json["issue_type"], "engineer_request")
        self.assertIn("Kya driver vehicle ke paas hai", result)

    def test_menu_service_returns_invalid_selection_message(self):
        service = MenuService(self.state_manager)

        result = service.handle_menu_selection(self.user.phone_number, "3")
        self.assertIn("Kripya valid option select kare", result)

    def test_support_flow_creates_main_menu_for_unknown_state(self):
        from app.services.user_service import get_or_create_user

        answer = handle_support_message(self.user, "hello", self.state_manager)
        self.assertIn("Namaste Anita Ji", answer)
        self.assertEqual(self.repository.states[self.user.phone_number].current_step, ConversationStep.MAIN_MENU.value)


if __name__ == "__main__":
    unittest.main()
