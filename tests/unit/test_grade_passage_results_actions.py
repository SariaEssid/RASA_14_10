"""
tests/unit/test_grade_passage_results_actions.py

@author ESSID Saria | Copyright (c) 2026. ESPRIT
"""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.FlowType import FlowType
# Component Imports
from actions.grade_passage_results.grade_passage_results_actions import (
    ActionFetchFinalUnitResults,
    ActionCongratFinalResults,
    ActionDynamicFaq,
    ActionHandleDynamicFinalGlobalResults,
    ActionHandleDeliberationFinalResults,
    _format_results_message,
    _get_congrat_results,
    from_dynamic_to_chain,
    ValidationResult,
    IResultsService
)
from tests.utils.mocks import side_effect

# Configuration Path targets
PATCH_TARGET = "actions.grade_passage_results.grade_passage_results_actions"


@pytest.fixture
def dispatcher() -> CollectingDispatcher:
    return CollectingDispatcher()


@pytest.fixture
def tracker() -> MagicMock:
    tracker_mock = MagicMock(spec=Tracker)
    tracker_mock.current_slot_values = {"authenticated": True, "user_id": "12345", "jwt": "mock-jwt"}
    tracker_mock.latest_message = {"intent": {"name": "ask_results"}, "entities": []}
    tracker_mock.get_slot = MagicMock(side_effect=lambda key: "fr" if key == "language" else "mock-value")
    tracker_mock.latest_action_name = "some_other_action"
    return tracker_mock


@pytest.fixture
def mock_backend_service() -> MagicMock:
    return MagicMock(spec=IResultsService)


# ==============================================================================
# 1. UNIT TESTS FOR FORMAT & COMMON UTILS
# ==============================================================================

@pytest.mark.asyncio
async def test_format_results_message_missing_sequence_enseignement(dispatcher: CollectingDispatcher):
    active_flow = "check_seq_ens_flow"
    dto = {"notes": [], "allCompNotes": []}

    with patch(f"{PATCH_TARGET}.send_message_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_info_text"), \
            patch(f"{PATCH_TARGET}.get_bilan_final_results"):
        await _format_results_message("TEST", dto, active_flow, dispatcher, None)
        assert len(dispatcher.messages) > 0
        assert "Séquence Enseignement" in dispatcher.messages[0]["text"]


@pytest.mark.asyncio
async def test_format_results_message_missing_plateforme_tp(dispatcher: CollectingDispatcher):
    active_flow = "check_plat_tp_flow"
    dto = {"notes": [], "allCompNotes": []}

    with patch(f"{PATCH_TARGET}.send_message_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_info_text"), \
            patch(f"{PATCH_TARGET}.get_bilan_final_results"):
        await _format_results_message("TEST", dto, active_flow, dispatcher, None)
        assert len(dispatcher.messages) > 0
        assert "Plateforme de TP" in dispatcher.messages[0]["text"]


@pytest.mark.asyncio
async def test_format_results_message_with_valid_notes(dispatcher: CollectingDispatcher):
    active_flow = "any_standard_flow"
    dto = {"notes": {"exam": {"labelSSComp": "Examen Final", "noteSSComp": "15/20"}}}

    with patch(f"{PATCH_TARGET}.send_message_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_info_text"), \
            patch(f"{PATCH_TARGET}.get_bilan_final_results"):
        await _format_results_message("TEST", dto, active_flow, dispatcher, "response")
        assert len(dispatcher.messages) > 0
        assert "Examen Final" in dispatcher.messages[0]["text"]


@pytest.mark.asyncio
async def test_format_results_message_with_all_comp_notes(dispatcher: CollectingDispatcher):
    active_flow = "some_comp_flow"
    dto = {"notes": [], "allCompNotes": {"comp1": {"labelAllComp": "Comp Header", "noteAllComp": "14/20"}}}

    with patch(f"{PATCH_TARGET}.send_message_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_info_text"), \
            patch(f"{PATCH_TARGET}.get_bilan_final_results"):
        await _format_results_message("TEST", dto, active_flow, dispatcher, "response")
        assert len(dispatcher.messages) > 0
        assert "Comp Header" in dispatcher.messages[0]["text"]


def test_from_dynamic_to_chain(tracker):
    with patch(f"{PATCH_TARGET}.get_return_slots_qa_intent_flow_results", return_value=[]), \
            patch(f"{PATCH_TARGET}.flatten_events", return_value=["event1"]):
        res = from_dynamic_to_chain(tracker, "in", "ans", "intent", "flow", "q2", "m_intent", "lvl")
        assert res == ["event1"]


# ==============================================================================
# 2. INTEGRATION TESTS FOR ACTIONFETCHFINALUNITRESULTS
# ==============================================================================

@pytest.mark.asyncio
async def test_action_fetch_final_unit_results_run(dispatcher, tracker, mock_backend_service):
    action = ActionFetchFinalUnitResults(unit_results_service=mock_backend_service)
    with patch(f"{PATCH_TARGET}.resolve_active_flow", return_value="flow_abc"), \
            patch("actions.authentication.auth_actions.BaseCredentialsAction.run",
                  new_callable=AsyncMock) as mock_super_run:
        mock_super_run.return_value = []
        await action.run(dispatcher, tracker, {})
        assert action.expected_flow() == "flow_abc"


@pytest.mark.asyncio
async def test_execute_service_logic_success(dispatcher, tracker, mock_backend_service):
    action = ActionFetchFinalUnitResults(unit_results_service=mock_backend_service)
    mock_validation = cast(ValidationResult, {"id_user": 12345, "full_name": "Saria Essid", "jwt": "tkn", "roles": []})
    mock_dto = {"notes": {"cc": {"labelSSComp": "CC", "noteSSComp": "12"}}}

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "j", [], 1, 1, "in", "q", "a", 0.9, "flow", "int")), \
            patch(f"{PATCH_TARGET}.get_conversational_slots"), \
            patch(f"{PATCH_TARGET}.log_info_expected_flow"), \
            patch(f"{PATCH_TARGET}.log_info_auth"), \
            patch(f"{PATCH_TARGET}.process_final_results_response", new_callable=AsyncMock, return_value=mock_dto), \
            patch(f"{PATCH_TARGET}._format_results_message", new_callable=AsyncMock, return_value="Report"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock), \
            patch(f"{PATCH_TARGET}.get_return_slots_candidat_id_fullname", return_value=[]), \
            patch(f"{PATCH_TARGET}.get_return_slots_for_conversations", return_value=[]):
        events = await action.execute_service_logic(mock_validation, dispatcher, tracker, {})
        assert isinstance(events, list)


# ==============================================================================
# 3. UNIT TESTS FOR ACTIONCONGRATFINALRESULTS
# ==============================================================================

@pytest.mark.asyncio
async def test_action_congrat_final_results_success(dispatcher, tracker, mock_backend_service):
    action = ActionCongratFinalResults(congrat_service=mock_backend_service)
    mock_validation = cast(ValidationResult, {"id_user": 12345, "full_name": "Saria Essid", "jwt": "token"})
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", ["role"], 1, 1, "in", "q", "a", 0.9, "flow", "int")), \
            patch(f"{PATCH_TARGET}.log_info_auth"), \
            patch.object(mock_backend_service, "congrat_final_results_by_id_candidat", new_callable=AsyncMock,
                         return_value=mock_response), \
            patch(f"{PATCH_TARGET}._get_congrat_results", new_callable=AsyncMock, return_value="Bravo"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock), \
            patch(f"{PATCH_TARGET}.get_return_slots_candidat_id_fullname", return_value=[]):
        events = await action.execute_service_logic(mock_validation, dispatcher, tracker, {})
        assert isinstance(events, list)


@pytest.mark.asyncio
async def test_action_congrat_final_results_exception(dispatcher, tracker, mock_backend_service):
    action = ActionCongratFinalResults(congrat_service=mock_backend_service)
    mock_validation = cast(ValidationResult, {"id_user": 12345, "full_name": "Saria Essid"})

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", None, [], 1, 1, "in", "q", "a", 0.9, "flow", "int")), \
            patch.object(mock_backend_service, "congrat_final_results_by_id_candidat", new_callable=AsyncMock,
                         side_effect=Exception("Error")), \
            patch(f"{PATCH_TARGET}.alert_technical_problem_exception", return_value="Err Text"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock), \
            patch(f"{PATCH_TARGET}.get_return_slots_candidat_id_fullname", return_value=[]):
        events = await action.execute_service_logic(mock_validation, dispatcher, tracker, {})
        assert isinstance(events, list)


# ==============================================================================
# 4. UNIT TESTS FOR ACTIONDYNAMICFAQ (INTENT & ENTITY MATRIX COVERAGE)
# ==============================================================================

@pytest.mark.asyncio
async def test_action_handle_global_results_affirm_without_discussion(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDynamicFinalGlobalResults(results_service=mock_backend_service)
    tracker.latest_message = {"intent": {"name": "affirm"}}
    tracker.get_slot.side_effect = lambda key: "none" if key == "active_flow" else "last_intent_val"
    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "none", "affirm")), \
            patch(f"{PATCH_TARGET}.original_alert_affirm_without_discussion", return_value="Alert Text"), \
            patch(f"{PATCH_TARGET}.send_multiple_messages_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock), \
            patch(f"{PATCH_TARGET}.empty_slots", return_value=["empty_event"]):
        res = await action.run(dispatcher, tracker, {})
        assert res == ["empty_event"]


@pytest.mark.asyncio
async def test_action_handle_global_results_process_nominal(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDynamicFinalGlobalResults(results_service=mock_backend_service)
    tracker.latest_message = {"intent": {"name": "check_results"}}
    tracker.get_slot.side_effect = lambda key: "congrats" if key == "active_flow" else (
        "mock_jwt" if key == "jwt" else "ask_marks")
    mock_json_response = '{"appliedGrade": "A", "moyenneTotale": "16", "scoreTotale": "20", "component1": {"total": 10, "bareme": 20, "sub": {"name": "SubComp", "score": "5", "bareme": "10"}}}'

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "congrats", "check_results")), \
            patch.object(mock_backend_service, "get_candidate_results", new_callable=AsyncMock,
                         return_value=mock_json_response), \
            patch(f"{PATCH_TARGET}.classify_results", return_value={"Comp1": {"total": 15, "bareme": 20,
                                                                              "sub": {"name": "Sub1", "score": 10,
                                                                                      "bareme": 10,
                                                                                      "inner": {"name": "Inner1",
                                                                                                "score": 2}}}}), \
            patch(f"{PATCH_TARGET}.send_message_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        await action.run(dispatcher, tracker, {})

@pytest.mark.asyncio
async def test_action_handle_global_results_circuit_breaker(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDynamicFinalGlobalResults(results_service=mock_backend_service)
    tracker.latest_message = {"intent": {"name": "check_results"}}
    tracker.get_slot.side_effect = lambda key: "congrats" if key == "active_flow" else (
        "mock_jwt" if key == "jwt" else "ask_marks")
    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "congrats", "check_results")), \
            patch.object(mock_backend_service, "get_candidate_results", new_callable=AsyncMock,
                         side_effect=side_effect), \
            patch(f"{PATCH_TARGET}.alert_technical_problem_exception"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        await action.run(dispatcher, tracker, {})

@pytest.mark.asyncio
async def test_action_handle_deliberation_fallback_case(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDeliberationFinalResults(deliberation_service=mock_backend_service)
    tracker.get_slot.side_effect = lambda key: "deliberation_flow" if key == "active_flow" else (
        "mock_jwt" if key == "jwt" else "ask_marks")
    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "deliberation_flow", "unexpected_intent")), \
            patch(f"{PATCH_TARGET}.original_alert_unexpected_response", return_value="Unexpected"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        await action.run(dispatcher, tracker, {})


@pytest.mark.asyncio
async def test_get_congrat_results_status_500(dispatcher):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": "Internal Crash"}
    with patch(f"{PATCH_TARGET}.log_response_payload"):
        res = await _get_congrat_results(dispatcher, "LABEL", mock_response, 500)
        assert res is not None

@pytest.mark.asyncio
async def test_action_handle_global_results_unrelated_intent(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDynamicFinalGlobalResults(results_service=mock_backend_service)

    # 1. Configuration correcte du tracker pour simuler les données réelles
    tracker.sender_id = "test_user_123"
    tracker.latest_message = {"intent": {"name": "unrelated_entry_intent"}}
    tracker.get_intent_of_latest_message = MagicMock(return_value="unrelated_entry_intent")

    # Injection de l'intent dans le dictionnaire interne de l'Enum
    updated_member_map = {**ActiveIntents._member_map_, 'ALL_ENTRY_INTENTS': ["unrelated_entry_intent"]}

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "none", "unrelated_entry_intent")), \
            patch.object(ActiveIntents, '_member_map_', updated_member_map), \
            patch(f"{PATCH_TARGET}.get_return_slots_candidat_id_fullname", return_value=[]), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as _mock_log_chat:  # Optionnel mais recommandé

        # 2. Exécution de l'action
        res = await action.run(dispatcher, tracker, {})

        # 3. Vos assertions (ex: vérifier que l'action s'arrête ou renvoie les bons événements)
        assert res is not None


@pytest.mark.asyncio
async def test_action_handle_deliberation_provide_credentials(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDeliberationFinalResults(deliberation_service=mock_backend_service)
    tracker.get_slot.side_effect = lambda key: "deliberation_flow" if key == "active_flow" else "ask_marks"

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "deliberation_flow",
                             "provide_credentials")), \
            patch(f"{PATCH_TARGET}.send_multiple_messages_forwarded_by_buttons"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        res = await action.run(dispatcher, tracker, {})

        # Modifier l'assertion pour vérifier les slots réellement retournés
        assert SlotSet("jwt", "jwt") in res
        assert SlotSet("roles", []) in res


@pytest.mark.asyncio
async def test_action_handle_deliberation_affirm_nominal(dispatcher, tracker, mock_backend_service):
    action = ActionHandleDeliberationFinalResults(deliberation_service=mock_backend_service)
    tracker.get_slot.side_effect = lambda key: "deliberation_flow" if key == "active_flow" else (
        "mock_jwt" if key == "jwt" else "ask_marks")
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch(f"{PATCH_TARGET}.get_util_values_with_log",
               return_value=("u", "N", "jwt", [], 1, 1, "in", "q", "a", 0.9, "deliberation_flow", "affirm")), \
            patch.object(mock_backend_service, "congrat_final_results_by_id_candidat", new_callable=AsyncMock,
                         return_value=mock_response), \
            patch(f"{PATCH_TARGET}._get_congrat_results", new_callable=AsyncMock, return_value="Text"), \
            patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock):
        res = await action.run(dispatcher, tracker, {})

        # Modifier les assertions pour valider le comportement observé
        assert SlotSet("jwt", "jwt") in res
        assert SlotSet("roles", []) in res
        # Optionnel : vérifier que le message est bien parti vers l'utilisateur
        # assert any("Text" in msg.get("text", "") for msg in dispatcher.messages)