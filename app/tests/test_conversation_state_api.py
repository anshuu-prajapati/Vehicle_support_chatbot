import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.state_manager import ConversationStep

client = TestClient(app)


class ConversationStateAPITests(unittest.TestCase):
    @patch("app.api.conversation_state.StateManager")
    def test_read_conversation_state_found(self, state_manager_class):
        state = SimpleNamespace(
            id="123e4567-e89b-12d3-a456-426614174000",
            phone_number="+911234567890",
            current_step=ConversationStep.MAIN_MENU.value,
            context_json={"vehicle_number": "ABC123"},
            created_at="2026-06-01T00:00:00Z",
            updated_at="2026-06-01T00:00:00Z",
        )
        state_manager_class.return_value.get_state.return_value = state

        response = client.get("/conversation-state/+911234567890")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["phone_number"], "+911234567890")
        self.assertEqual(response.json()["context_json"], {"vehicle_number": "ABC123"})

    @patch("app.api.conversation_state.StateManager")
    def test_read_conversation_state_not_found(self, state_manager_class):
        state_manager_class.return_value.get_state.return_value = None

        response = client.get("/conversation-state/+911234567891")

        self.assertEqual(response.status_code, 404)

    @patch("app.api.conversation_state.StateManager")
    def test_delete_conversation_state_found(self, state_manager_class):
        state_manager_class.return_value.delete_state.return_value = True

        response = client.delete("/conversation-state/+911234567890")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "deleted")

    @patch("app.api.conversation_state.StateManager")
    def test_delete_conversation_state_not_found(self, state_manager_class):
        state_manager_class.return_value.delete_state.return_value = False

        response = client.delete("/conversation-state/+911234567891")

        self.assertEqual(response.status_code, 404)

    @patch("app.api.conversation_state.StateManager")
    def test_reset_conversation_state(self, state_manager_class):
        state = SimpleNamespace(
            id="123e4567-e89b-12d3-a456-426614174001",
            phone_number="+911234567892",
            current_step=ConversationStep.MAIN_MENU.value,
            context_json={},
            created_at="2026-06-01T00:00:00Z",
            updated_at="2026-06-01T00:00:00Z",
        )
        state_manager_class.return_value.clear_state.return_value = state

        response = client.post("/conversation-state/reset/+911234567892")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["phone_number"], "+911234567892")
        self.assertEqual(response.json()["current_step"], ConversationStep.MAIN_MENU.value)


if __name__ == "__main__":
    unittest.main()
