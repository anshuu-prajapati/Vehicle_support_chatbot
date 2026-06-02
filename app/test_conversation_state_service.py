import unittest

from app.services.conversation_state_service import (
    is_valid_state,
    validate_state_name,
    validate_transition,
    ASK_HELP_TYPE,
    FLEET_ALERT_CREATED,
    WAITING_MANAGER_REPLY,
    WAITING_NEW_CONTACT_NAME,
    WAITING_NEW_CONTACT_PHONE,
    CLOSED,
)


class ConversationStateServiceTests(unittest.TestCase):
    def test_valid_state_names(self):
        self.assertTrue(is_valid_state(ASK_HELP_TYPE))
        self.assertTrue(is_valid_state(FLEET_ALERT_CREATED))
        self.assertTrue(is_valid_state(WAITING_MANAGER_REPLY))
        self.assertTrue(is_valid_state(WAITING_NEW_CONTACT_NAME))
        self.assertTrue(is_valid_state(WAITING_NEW_CONTACT_PHONE))
        self.assertTrue(is_valid_state(CLOSED))

    def test_invalid_state_name_raises(self):
        with self.assertRaises(ValueError):
            validate_state_name("UNKNOWN_STATE")

    def test_valid_transition_rules(self):
        validate_transition(ASK_HELP_TYPE, FLEET_ALERT_CREATED)
        validate_transition(FLEET_ALERT_CREATED, WAITING_NEW_CONTACT_NAME)
        validate_transition(WAITING_NEW_CONTACT_NAME, WAITING_NEW_CONTACT_PHONE)
        validate_transition(WAITING_NEW_CONTACT_PHONE, WAITING_MANAGER_REPLY)
        validate_transition(WAITING_MANAGER_REPLY, CLOSED)
        validate_transition(CLOSED, CLOSED)

    def test_invalid_transition_raises(self):
        with self.assertRaises(ValueError):
            validate_transition(CLOSED, ASK_HELP_TYPE)

        with self.assertRaises(ValueError):
            validate_transition(ASK_HELP_TYPE, CLOSED)


if __name__ == "__main__":
    unittest.main()
