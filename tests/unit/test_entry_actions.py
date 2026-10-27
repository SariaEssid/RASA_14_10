"""
tests/unit/test_entry_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.entry.entry_actions import ActionGetDynamicResponse, ActionGetNextDetails
from actions.utils.interfaces import IResultsService
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.FlowType import FlowType
from aiocircuitbreaker import CircuitBreakerError

PATCH_TARGET = "actions.entry.entry_actions"


# ==============================================================================
# REUSABLE TESTING FIXTURES
# ==============================================================================

@pytest.fixture
def mock_service() -> MagicMock:
    service = MagicMock(spec=IResultsService)
    service.get_dynamic_response = AsyncMock(return_value={"reply": "Mocked validation target response"})
    service.get_next_detailed_response = AsyncMock(return_value="Detailed structural mock execution path data response")
    return service


@pytest.fixture
def tracker() -> MagicMock:
    tracker_mock = MagicMock(spec=Tracker)
    tracker_mock.sender_id = "pfe_tester_saria"
    tracker_mock.latest_action_name = "some_previous_action"

    # ✅ FIX: Define the events attribute so get_conversational_slots doesn't crash
    tracker_mock.events = []

    # Context state dictionary setup
    tracker_mock.latest_message = {
        "text": "Quels sont les critères d'évaluation ?",
        "intent": {"name": "ask_criteres_evaluations_sscomp", "confidence": 0.99}
    }

    slots = {
        "session_id": "session_entry_xyz123",
        "active_flow": "initial_flow_state",
        "sscomp": "architecture_software",
        "last_question": "initial question text"
    }

    tracker_mock.get_slot = MagicMock(side_effect=lambda key: slots.get(key))
    tracker_mock.get_intent_of_latest_message = MagicMock(return_value="ask_criteres_evaluations_sscomp")

    # Store reference context dictionary for quick modification within test scope blocks
    tracker_mock._test_slots = slots
    return tracker_mock

@pytest.mark.asyncio
@pytest.mark.parametrize("intent,flow,expected_intent,expected_flow", [
    (ActiveIntents.ASK_AFFIRM.value, FlowType.GIVE_ADVICE_1.value, ActiveIntents.AFFIRM_ADVICE_2.value,
     "give_advice_2"),
    (ActiveIntents.ASK_AFFIRM.value, FlowType.GIVE_ADVICE_2.value, ActiveIntents.AFFIRM_ADVICE_3.value,
     "give_advice_3"),
])
async def test_action_get_dynamic_response_advice_flow_mutations(
        dispatcher, tracker, mock_service, intent, flow, expected_intent, expected_flow
):
    action = ActionGetDynamicResponse(mock_service)

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", [], "usr_1", "sess_1", "Affirmative message text", "lq", "la", 0.95, flow, intent
    )), patch(f"{PATCH_TARGET}.get_semantic_random_reply", return_value="Step execution guide reply text"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as _mock_log:
        await action.run(dispatcher, tracker, {})

        # Verify targeted modification of incoming routing parameters inside pipeline payload creation
        mock_service.get_dynamic_response.assert_called_with({
            "userInput": "affirmative message text",
            "intent": expected_intent,
            "userId": "usr_1"
        })


@pytest.mark.asyncio
async def test_action_get_dynamic_response_json_string_parsing_fallback(dispatcher, tracker, mock_service):
    action = ActionGetDynamicResponse(mock_service)
    mock_service.get_dynamic_response = AsyncMock(return_value=json.dumps({"reply": "Extracted value matrix"}))

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", "usr_1", "sess_1", "Plain text dynamic lookup query", "lq", "la", 0.99, "flow",
            "generic_intent"
    )), patch(f"{PATCH_TARGET}.get_semantic_random_reply",
              return_value="Extracted answer message string block") as mock_random_reply, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        await action.run(dispatcher, tracker, {})

        # ✅ FIX: Match the real string token value expected by the actual implementation 'PY-7-DYNAMIC-RESPONSE'
        mock_random_reply.assert_called_once_with({"reply": "Extracted value matrix"}, "PY-7-DYNAMIC-RESPONSE",
                                                  "Plain text dynamic lookup query")


@pytest.mark.asyncio
@pytest.mark.parametrize("target_intent,question_text", [
    (FlowType.GREET.value, "Bonjour"),
    (ActiveIntents.ASK_ABOUT_CANDIDATURE_PASSAGE_GRADE.value, "Comment se passe le PFE ?"),
    (ActiveIntents.STRESSED_CANDIDAT.value, "/stressed_candidat"),
    (ActiveIntents.STRESSED_CANDIDAT.value, "Je panique un peu face aux jurys"),
    (ActiveIntents.ASK_CRITERES_EVALUATIONS_SSCOMP.value, "Quels sont les barèmes ?")
])
async def test_action_get_dynamic_response_intent_routing_outputs(dispatcher, tracker, mock_service, target_intent,
                                                                  question_text):
    # ✅ FIX: Re-instantiate/clear dispatcher messages for isolated parameter verification loops
    dispatcher.messages.clear()
    action = ActionGetDynamicResponse(mock_service)

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", "usr_1", "sess_1", question_text, "lq", "la", 0.95, "flow_ctx", target_intent
    )), patch(f"{PATCH_TARGET}.get_semantic_random_reply",
              return_value="Dynamic structured evaluation reply context mapping response value"), \
            patch(f"{PATCH_TARGET}.send_multiple_messages_forwarded_by_buttons") as mock_send_buttons, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):

        await action.run(dispatcher, tracker, {})

        if target_intent == FlowType.GREET.value:
            assert len(dispatcher.messages) == 1
            assert dispatcher.messages[0][
                       "text"] == "Dynamic structured evaluation reply context mapping response value"
        elif target_intent == ActiveIntents.STRESSED_CANDIDAT.value and question_text == "/stressed_candidat":
            assert len(dispatcher.messages) == 1
            assert "mini guide" in dispatcher.messages[0]["text"]
        else:
            # For other routes, custom messaging helper functions are invoked
            mock_send_buttons.assert_called_once()


# ==============================================================================
# 2. ActionGetDynamicResponse ERROR HANDLING BOUNDARY CONDITIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_action_get_dynamic_response_circuit_breaker_handling(dispatcher, tracker, mock_service):
    action = ActionGetDynamicResponse(mock_service)
    mock_service.get_dynamic_response.side_effect = CircuitBreakerError(MagicMock(), "Spring authentication circuit open")

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", "usr_1", "sess_1", "text", "lq", "la", 0.9, "flow", "intent"
    )), patch(f"{PATCH_TARGET}.alert_technical_problem_exception",
              return_value="Circuit broken answer context fallback") as mock_alert, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as _mock_log:
        await action.run(dispatcher, tracker, {})
        # ✅ FIX: Now that get_conversational_slots evaluates cleanly, it executes exactly 1 user message
        assert len(dispatcher.messages) == 1
        mock_alert.assert_called_once()
        _mock_log.assert_called_once_with("usr_1", "sess_1", "text", "Circuit broken answer context fallback", "intent",
                                         0.9)


@pytest.mark.asyncio
async def test_action_get_dynamic_response_key_error_handling(dispatcher, tracker, mock_service):
    action = ActionGetDynamicResponse(mock_service)
    mock_service.get_dynamic_response.side_effect = KeyError("missing_payload_field_key")

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", "usr_1", "sess_1", "text", "lq", "la", 0.9, "flow", "intent"
    )), patch(f"{PATCH_TARGET}.send_fallback_problem_to_dsi_forwarded_by_buttons",
              return_value="Key missing notification context fallback") as mock_fallback, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log:
        await action.run(dispatcher, tracker, {})
        mock_fallback.assert_called_once()
        mock_log.assert_called_once_with("usr_1", "sess_1", "text", "Key missing notification context fallback",
                                         "intent", 0.9)


@pytest.mark.asyncio
async def test_action_get_dynamic_response_json_decode_and_type_error_handling(dispatcher, tracker, mock_service):
    action = ActionGetDynamicResponse(mock_service)
    mock_service.get_dynamic_response.side_effect = TypeError("Invalid target serialization model format mapping")

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", "usr_1", "sess_1", "text", "lq", "la", 0.9, "flow", "intent"
    )), patch(f"{PATCH_TARGET}.send_fallback_problem_to_dsi_forwarded_by_buttons",
              return_value="Parsing type fallback error string representation") as mock_fallback, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log:
        await action.run(dispatcher, tracker, {})
        mock_fallback.assert_called_once()
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_action_get_dynamic_response_generic_exception_bubble_up(dispatcher, tracker, mock_service):
    action = ActionGetDynamicResponse(mock_service)

    # Configure the exception side effect before running the action logic
    mock_service.get_dynamic_response.side_effect = RuntimeError("Fatal hardware memory allocation overflow exception")

    # ✅ FIX: Wrap the execution context correctly to capture the __wrapped__ bubbling logic cleanly
    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", [], "usr_1", "sess_1", "text", "lq", "la", 0.9, "flow", "intent"
    )), patch(f"{PATCH_TARGET}.alert_technical_problem_exception",
              return_value="Fatal breakdown notification fallback text value"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="Fatal hardware memory allocation overflow exception"):
            await action.run.__wrapped__(action, dispatcher, tracker, {})


# ==============================================================================
# 3. ActionGetNextDetails COMPONENT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_action_get_next_details_successful_pipeline_execution(dispatcher, tracker, mock_service):
    action = ActionGetNextDetails(mock_service)
    assert action.name() == "action_get_next_details_response"

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user_saria", "Saria FullName", ["USER"], "usr_id_99", "sess_details_77",
            "User input text", "Calculated question context query text", "Previous bot output text block", 0.98,
            "active_details_flow_state", "request_details_intent"
    )), patch(f"{PATCH_TARGET}.send_multiple_messages_forwarded_by_buttons") as mock_send_buttons, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log:
        events = await action.run(dispatcher, tracker, {})

        mock_service.get_next_detailed_response.assert_called_once_with("usr_id_99")

        expected_buttons = [
            {'title': 'Composante 1', 'payload': '/select_comp_for_guide{"sscomp":"Composante 1"}'},
            {'title': 'Composante 2', 'payload': '/select_comp_for_guide{"sscomp":"Composante 2"}'},
            {'title': 'Composante 3', 'payload': '/select_comp_for_guide{"sscomp":"Composante 3"}'},
            {'title': '🔙 Retourner au Mini-Guide', 'payload': '/stressed_candidat'}
        ]

        mock_send_buttons.assert_called_once_with(
            dispatcher,
            "Detailed structural mock execution path data response",
            expected_buttons
        )

        mock_log.assert_called_once_with("usr_id_99", "sess_details_77", "User input text",
                                         "Detailed structural mock execution path data response",
                                         "request_details_intent", 0.98)

        assert events == [SlotSet("active_flow", "active_details_flow_state")]


@pytest.mark.asyncio
async def test_action_get_next_details_circuit_breaker_error_handling(dispatcher, tracker, mock_service):
    action = ActionGetNextDetails(mock_service)
    mock_service.get_next_detailed_response.side_effect = CircuitBreakerError(MagicMock(),
                                                                              "Details microservice pipeline closed")

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", [], "usr_1", "sess_1", "user_input", "q", "a", 0.9, "details_flow", "intent"
    )), patch(f"{PATCH_TARGET}.alert_technical_problem_exception",
              return_value="Circuit open detail recovery text block") as mock_alert, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log:
        events = await action.run(dispatcher, tracker, {})
        assert len(dispatcher.messages) == 1
        mock_alert.assert_called_once()
        mock_log.assert_called_once()
        assert events == [SlotSet("active_flow", "details_flow")]


@pytest.mark.asyncio
async def test_action_get_next_details_key_error_handling(dispatcher, tracker, mock_service):
    action = ActionGetNextDetails(mock_service)
    mock_service.get_next_detailed_response.side_effect = KeyError("target_details_index_error")

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", [], "usr_1", "sess_1", "user_input", "q", "a", 0.9, "details_flow", "intent"
    )), patch(f"{PATCH_TARGET}.send_fallback_problem_to_dsi_forwarded_by_buttons",
              return_value="Key fallback representation") as mock_fallback, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log:
        events = await action.run(dispatcher, tracker, {})
        mock_fallback.assert_called_once()
        mock_log.assert_called_once()
        assert events == [SlotSet("active_flow", "details_flow")]


@pytest.mark.asyncio
async def test_action_get_next_details_json_decode_and_type_error_handling(dispatcher, tracker, mock_service):
    action = ActionGetNextDetails(mock_service)
    mock_service.get_next_detailed_response.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)

    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", [], "usr_1", "sess_1", "user_input", "q", "a", 0.9, "details_flow", "intent"
    )), patch(f"{PATCH_TARGET}.send_fallback_problem_to_dsi_forwarded_by_buttons",
              return_value="JSON corruption response text override value") as mock_fallback, \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log:
        events = await action.run(dispatcher, tracker, {})
        mock_fallback.assert_called_once()
        mock_log.assert_called_once()
        assert events == [SlotSet("active_flow", "details_flow")]


@pytest.mark.asyncio
async def test_action_get_next_details_generic_exception_bubbling(dispatcher, tracker, mock_service):
    action = ActionGetNextDetails(mock_service)

    # Configure the exception side effect before running the action logic
    mock_service.get_next_detailed_response.side_effect = ValueError("Corrupted system input encoding profile")

    # ✅ FIX: Wrap the execution context correctly to capture the __wrapped__ bubbling logic cleanly
    with patch(f"{PATCH_TARGET}.get_util_values_with_log", return_value=(
            "user", "Saria", [], "usr_1", "sess_1", "user_input", "q", "a", 0.9, "details_flow", "intent"
    )), patch(f"{PATCH_TARGET}.alert_technical_problem_exception",
              return_value="Generic crash payload string text block"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        with pytest.raises(ValueError, match="Corrupted system input encoding profile"):
            await action.run.__wrapped__(action, dispatcher, tracker, {})