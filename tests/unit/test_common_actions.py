"""
tests/unit/test_common_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from unittest.mock import MagicMock, patch

from actions.util_actions.common_actions import get_slot_safe, ActionUtterBotTyping


# ==============================================================================
# 1. TESTS FOR get_slot_safe
# ==============================================================================

def test_get_slot_safe_found_in_events():
    """Verify get_slot_safe extracts the latest value from the tracker events list."""
    tracker = MagicMock()
    tracker.events = [
        {"event": "slot", "name": "last_question", "value": "Old question"},
        {"event": "user", "text": "Some text"},
        {"event": "slot", "name": "last_question", "value": "Latest question"},
        {"event": "bot", "text": "Hello"}
    ]

    result = get_slot_safe(tracker, "last_question")
    assert result == "Latest question"
    tracker.get_slot.assert_not_called()


def test_get_slot_safe_fallback_to_get_slot():
    """Verify get_slot_safe falls back to tracker.get_slot if not found in events."""
    tracker = MagicMock()
    tracker.events = [
        {"event": "slot", "name": "different_slot", "value": "value"},
        {"event": "user", "text": "hello"}
    ]
    tracker.get_slot.return_value = "Fallback Value"

    result = get_slot_safe(tracker, "last_question")
    assert result == "Fallback Value"
    tracker.get_slot.assert_called_once_with("last_question")


# ==============================================================================
# 2. TESTS FOR ActionUtterBotTyping
# ==============================================================================

def test_action_utter_bot_typing_name():
    """Verify the action returns the correct registration name."""
    action = ActionUtterBotTyping()
    assert action.name() == "action_bot_typing"


@patch("actions.util_actions.common_actions.log_info_text")
def test_action_utter_bot_typing_run(mock_log_info):
    """Verify the run method utters the typing indicator and captures slots successfully."""
    action = ActionUtterBotTyping()
    dispatcher = MagicMock()
    tracker = MagicMock()
    domain = {}

    # Mock event stream for get_slot_safe tracking
    tracker.events = [
        {"event": "slot", "name": "last_question", "value": "How to register?"},
        {"event": "slot", "name": "last_last_question", "value": "What is RASA?"},
        {"event": "slot", "name": "last_answer", "value": "Rasa is an AI framework."}
    ]

    # Mock current instant slot values mapping
    tracker.current_slot_values.return_value = {
        "last_last_question": "What is RASA?",
        "last_question": "How to register?",
        "last_answer": "Rasa is an AI framework."
    }

    # Mock tracker fallback tracker.get_slot results
    def side_effect_get_slot(slot_name):
        slots = {
            "last_last_question": "What is RASA?",
            "last_question": "How to register?",
            "last_answer": "Rasa is an AI framework."
        }
        return slots.get(slot_name)

    tracker.get_slot.side_effect = side_effect_get_slot

    # Execute action lifecycle wrapper method
    events_result = action.run(dispatcher, tracker, domain)

    # Assetions
    assert events_result == []
    dispatcher.utter_message.assert_called_once_with(text="Pensé en cours ...⏳")

    # Verify that the internal logging tool calls tracker information
    assert mock_log_info.call_count == 9  # 3 distinct print groups x 3 parameters monitored