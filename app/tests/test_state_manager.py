import unittest
from unittest.mock import MagicMock, patch

from app.services.state_manager import (
    DEFAULT_STATE_CONTEXT,
    ConversationStep,
    StateManager,
)


class DummyState:
    def __init__(self, phone_number, current_step, context_json=None):
        self.phone_number = phone_number
        self.current_step = current_step
        self.context_json = context_json or {}


class DummyRepository:
    def __init__(self):
        self.states = {}
        self.created = []
        self.updated = []
        self.deleted = []

    def get_by_phone(self, phone_number):
        return self.states.get(phone_number)

    def get_by_phone_for_update(self, phone_number):
        return self.states.get(phone_number)

    def create(self, phone_number, current_step, context_json=None):
        state = DummyState(phone_number, current_step, context_json)
        self.states[phone_number] = state
        self.created.append(state)
        return state

    def update(self, state, current_step=None, context_json=None):
        if current_step is not None:
            state.current_step = current_step
        if context_json is not None:
            state.context_json = context_json
        self.updated.append(state)
        return state

    def delete_by_phone(self, phone_number):
        state = self.states.pop(phone_number, None)
        if state:
            self.deleted.append(phone_number)
            return True
        return False


class StateManagerTests(unittest.TestCase):
    def setUp(self):
        self.repository = DummyRepository()
        self.state_manager = StateManager(db=MagicMock(), repository=self.repository)

    def test_set_state_creates_new_state(self):
        state = self.state_manager.set_state("+911234567890", ConversationStep.VEHICLE_NUMBER)

        self.assertEqual(state.current_step, ConversationStep.VEHICLE_NUMBER.value)
        self.assertEqual(state.context_json, DEFAULT_STATE_CONTEXT)
        self.assertIn("+911234567890", self.repository.states)

    def test_set_state_reuses_existing_context_when_none(self):
        self.repository.create("+911234567890", ConversationStep.MAIN_MENU.value, {"vehicle_number": "123"})

        state = self.state_manager.set_state("+911234567890", ConversationStep.ASK_LOCATION)

        self.assertEqual(state.current_step, ConversationStep.ASK_LOCATION.value)
        self.assertEqual(state.context_json, {"vehicle_number": "123"})

    def test_update_context_creates_new_state_when_missing(self):
        state = self.state_manager.update_context(
            "+911234567890",
            {"vehicle_number": "ABC123"},
            current_step=ConversationStep.VEHICLE_NUMBER,
        )

        self.assertEqual(state.current_step, ConversationStep.VEHICLE_NUMBER.value)
        self.assertEqual(state.context_json["vehicle_number"], "ABC123")

    def test_update_context_merges_with_existing(self):
        existing = self.repository.create(
            "+911234567890",
            ConversationStep.MAIN_MENU.value,
            {"vehicle_number": "ABC123", "location": "Delhi"},
        )

        state = self.state_manager.update_context(
            "+911234567890",
            {"location": "Mumbai", "owner_name": "Anshu"},
            current_step=ConversationStep.ASK_IGNITION,
        )

        self.assertEqual(state.current_step, ConversationStep.ASK_IGNITION.value)
        self.assertEqual(state.context_json["vehicle_number"], "ABC123")
        self.assertEqual(state.context_json["location"], "Mumbai")
        self.assertEqual(state.context_json["owner_name"], "Anshu")

    def test_clear_state_resets_context(self):
        self.repository.create(
            "+911234567890",
            ConversationStep.ASK_LOCATION.value,
            {"vehicle_number": "ABC123"},
        )

        state = self.state_manager.clear_state("+911234567890")

        self.assertEqual(state.current_step, ConversationStep.MAIN_MENU.value)
        self.assertEqual(state.context_json, DEFAULT_STATE_CONTEXT)

    def test_delete_state_returns_false_if_missing(self):
        deleted = self.state_manager.delete_state("+911234567890")
        self.assertFalse(deleted)

    def test_delete_state_returns_true_when_present(self):
        self.repository.create(
            "+911234567890",
            ConversationStep.MAIN_MENU.value,
        )

        deleted = self.state_manager.delete_state("+911234567890")
        self.assertTrue(deleted)


if __name__ == "__main__":
    unittest.main()
