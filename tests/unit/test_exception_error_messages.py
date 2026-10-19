"""
tests/unit/test_exception_error_messages.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import pytest
from unittest.mock import MagicMock, patch
from actions.utils.exception_error_messages import (
    exception_llm_err,
    exception_fallback_err,
    exception_llm_err_dsi,
    exception_fallback_err_dsi,
    unexpected_exception_dsi
)
from actions.constants.Constants import FEEDBACK_BUTTONS


@pytest.fixture
def mock_dispatcher():
    """Fixture pour simuler le CollectingDispatcher de Rasa."""
    return MagicMock()


def test_exception_llm_err(mock_dispatcher):
    # Action
    result = exception_llm_err(mock_dispatcher)

    # Assertions
    expected_msg = "😢 Désolé, je n'ai pas réussi à générer la réponse. \nPeux-tu reformuler ? 🙏"
    assert result == expected_msg
    mock_dispatcher.utter_message.assert_called_once_with(expected_msg)


def test_exception_fallback_err(mock_dispatcher):
    # Action
    exception_fallback_err(mock_dispatcher)

    # Assertions
    expected_msg = "😕 Oups… une erreur de réseau est survenue. \nRéessaye dans un instant 🙏"
    mock_dispatcher.utter_message.assert_called_once_with(expected_msg)


@patch("actions.utils.exception_error_messages.send_custom_fallback_problem_to_dsi_forwarded_by_buttons")
async def test_exception_llm_err_dsi(mock_send_dsi, mock_dispatcher):
    # Setup
    action_label = "action_test"
    payload = {"text": "hello"}
    err_str = "Timeout connection"

    # Action
    await exception_llm_err_dsi(mock_dispatcher, action_label, payload, err_str)

    # Assertions
    mock_send_dsi.assert_called_once_with(
        mock_dispatcher, action_label, payload, err_str, "💥 Fatal LLM Error: ", FEEDBACK_BUTTONS
    )


@patch("actions.utils.exception_error_messages.send_custom_fallback_problem_to_dsi_forwarded_by_buttons")
async def test_exception_fallback_err_dsi(mock_send_dsi, mock_dispatcher):
    # Setup
    action_label = "action_test"
    payload = {"text": "hello"}
    err_str = "Fallback failed"

    # Action
    await exception_fallback_err_dsi(mock_dispatcher, action_label, payload, err_str)

    # Assertions
    mock_send_dsi.assert_called_once_with(
        mock_dispatcher, action_label, payload, err_str, "❌ Fallback LLM also failed: ", FEEDBACK_BUTTONS
    )


@patch("actions.utils.exception_error_messages.get_random_message")
@patch("actions.utils.exception_error_messages.send_custom_fallback_problem_to_dsi_forwarded_by_buttons")
async def test_unexpected_exception_dsi(mock_send_dsi, mock_get_random, mock_dispatcher):
    # Setup
    action_label = "action_test"
    payload = {"text": "hello"}
    err_str = "Unexpected crash"

    # On force le message aléatoire à être fixe pour le test
    mock_get_random.return_value = "Message DSI Aléatoire"
    # On simule la valeur de retour du helper dsi
    mock_send_dsi.return_value = "DSI_NOTIFIED"

    # Action
    result = await unexpected_exception_dsi(mock_dispatcher, action_label, payload, err_str)

    # Assertions
    mock_get_random.assert_called_once()
    mock_send_dsi.assert_called_once_with(
        mock_dispatcher, action_label, payload, err_str, "Message DSI Aléatoire", FEEDBACK_BUTTONS
    )
    assert result == "DSI_NOTIFIED"