"""
tests/unit/test_error_handling.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import logging
from unittest.mock import MagicMock, patch
import httpx
import pytest

from actions.utils.error_handling import handle_action_errors

logger = logging.getLogger(__name__)


# Helper utility class to match variable ISO format strings in dictionary assertions
class PytestAny:
    def __init__(self, type_hint):
        self.type_hint = type_hint
    def __eq__(self, other):
        return isinstance(other, self.type_hint)


@pytest.fixture
def mock_rasa_components():
    """Provides mocked instances of Rasa dispatcher, tracker, and domain."""
    dispatcher = MagicMock()
    tracker = MagicMock()
    domain = {}

    # Configure mock tracker properties for the fallback payload construction
    tracker.sender_id = "test_user_id"
    tracker.get_slot.return_value = "session_abc_123"
    tracker.latest_message = {
        "text": "Show my grades",
        "intent": {
            "name": "check_results",
            "confidence": 0.98
        }
    }
    return dispatcher, tracker, domain


@pytest.mark.asyncio
@patch("actions.utils.error_handling.name", create=True)
async def test_http_500_branch(mock_name, mock_rasa_components):
    """Verify HTTP status errors that fall through to the else branch are handled."""
    dispatcher, tracker, domain = mock_rasa_components
    mock_name.return_value = "test_action"

    class Action:
        # noinspection PyMethodMayBeStatic
        def name(self):
            return "test_action"

    @handle_action_errors
    async def f(_self, _disp, _trk, _dom):
        raise httpx.HTTPStatusError(
            "500",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(500)
        )

    result = await f(Action(), dispatcher, tracker, domain)
    assert result == []


@pytest.mark.asyncio
async def test_handle_action_errors_success(mock_rasa_components):
    """Verify the wrapper successfully forwards returns when no exception occurs."""
    dispatcher, tracker, domain = mock_rasa_components

    # Define a clean async dummy function wrapped by our decorator
    @handle_action_errors
    async def dummy_action(_self, _disp, _trk, _dom):
        return [{"event": "slot", "name": "test", "value": True}]

    result = await dummy_action(None, dispatcher, tracker, domain)
    assert result == [{"event": "slot", "name": "test", "value": True}]


@pytest.mark.asyncio
@patch("actions.utils.error_handling.name", create=True)
async def test_handle_action_errors_http_401(mock_name, mock_rasa_components):
    """Verify dispatcher utters failed authentication message on HTTP 401."""
    dispatcher, tracker, domain = mock_rasa_components
    mock_name.return_value = "DummyAction"

    # Simulate an HTTPStatusError with a 401 response status code
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized access token"

    @handle_action_errors
    async def dummy_action(_self, _disp, _trk, _dom):
        raise httpx.HTTPStatusError("Auth Error", request=MagicMock(), response=mock_response)

    result = await dummy_action(None, dispatcher, tracker, domain)

    assert result == []
    dispatcher.utter_message.assert_called_once()


@pytest.mark.asyncio
@patch("actions.utils.error_handling.name", create=True)
async def test_handle_action_errors_http_404(mock_name, mock_rasa_components):
    """Verify dispatcher utters result not found message on HTTP 404."""
    dispatcher, tracker, domain = mock_rasa_components
    mock_name.return_value = "DummyAction"

    # Simulate an HTTPStatusError with a 404 response status code
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = "Resource not found"

    @handle_action_errors
    async def dummy_action(_self, _disp, _trk, _dom):
        raise httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

    result = await dummy_action(None, dispatcher, tracker, domain)

    assert result == []
    dispatcher.utter_message.assert_called_once()


@pytest.mark.asyncio
@patch("actions.utils.error_handling.name", create=True)
async def test_handle_action_errors_http_other(mock_name, mock_rasa_components):
    """Verify dispatcher utters generic technical problem message on other HTTP status codes."""
    dispatcher, tracker, domain = mock_rasa_components
    mock_name.return_value = "DummyAction"

    # Simulate an HTTPStatusError with a 500 response status code
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    @handle_action_errors
    async def dummy_action(_self, _disp, _trk, _dom):
        raise httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response)

    result = await dummy_action(None, dispatcher, tracker, domain)

    assert result == []
    dispatcher.utter_message.assert_called_once()


@pytest.mark.asyncio
@patch("actions.utils.error_handling.send_fallback_problem_to_dsi_forwarded_by_buttons")
@patch("actions.utils.error_handling.name", create=True)
async def test_handle_action_errors_general_exception(mock_name, mock_send_fallback, mock_rasa_components):
    """Verify arbitrary exceptions are captured and forwarded to the DSI fallback workflow."""
    dispatcher, tracker, domain = mock_rasa_components
    mock_name.return_value = "DummyAction"

    expected_exception = RuntimeError("Database connection timed out")

    @handle_action_errors
    async def dummy_action(_self, _disp, _trk, _dom):
        raise expected_exception

    result = await dummy_action(None, dispatcher, tracker, domain)

    assert result == []
    mock_send_fallback.assert_called_once_with(
        dispatcher,
        "CENTRAL_HANDLING_ERROR",
        {
            "userId": "test_user_id",
            "sessionId": "session_abc_123",
            "userInput": "Show my grades",
            "rasaIntent": "check_results",
            "confidence": 0.98,
            "messageExchangeDate": PytestAny(str)  # Instantiating the proper helper class here
        },
        expected_exception
    )