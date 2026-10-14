"""
tests/unit/test_auth_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import pytest
import time
from typing import Dict, Any, List, Text
from unittest.mock import MagicMock, patch, AsyncMock
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.authentication.auth_actions import BaseCredentialsAction, ValidationResult
from actions.constants.ActiveIntents import ActiveIntents

# Définition du chemin cible pour les patchs
PATCH_TARGET = "actions.authentication.auth_actions"


# ==============================================================================
# SUBCLASS CONCRÈTE POUR LES TESTS UNITAIRES
# ==============================================================================
class ConcreteCredentialsAction(BaseCredentialsAction):
    def name(self) -> Text:
        return "action_concrete_credentials_test"

    def expected_flow(self) -> Text:
        return "mock_flow"

    async def execute_service_logic(
            self, validation: ValidationResult, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Comportement bouchon pour une exécution nominale réussie
        return [{"event": "slot", "name": "service_executed", "value": True}]


# ==============================================================================
# CONFIGURATION DES FIXTURES
# ==============================================================================
@pytest.fixture
def mock_service():
    service = MagicMock()
    service.verif_credentials = AsyncMock()
    return service


@pytest.fixture
def mock_dispatcher():
    return MagicMock(spec=CollectingDispatcher)


@pytest.fixture
def mock_tracker():
    tracker = MagicMock(spec=Tracker)
    tracker.get_slot.side_effect = lambda key: ActiveIntents.ASK_PROCEDURE_PG.value if key == "last_intent" else None
    tracker.latest_message = {"text": "user123 pwd123", "intent": {"confidence": 0.95}}
    tracker.sender_id = "test_sender"
    tracker.get_intent_of_latest_message.return_value = "provide_credentials"
    return tracker


@pytest.fixture
def mock_settings():
    with patch(f"{PATCH_TARGET}.settings") as mocked_settings:
        mocked_settings.TOTAL_WAIT_SECONDS = 300  # 5 minutes
        mocked_settings.INVALID_CREDENTIALS_TENTATIVE_COUNT = 3
        yield mocked_settings


@pytest.fixture
def auth_action(mock_service):
    return ConcreteCredentialsAction(service=mock_service)

def test_auth_failure_tracking_and_reset(auth_action, mock_settings):
    """Test unitaire isolé des méthodes internes de suivi et de nettoyage des tentatives."""
    session_id, username = "sess_456", "test_user"

    # 1. Premier échec
    auth_action._track_auth_failure(session_id, username)
    key = f"{session_id}_{username}"
    assert auth_action._auth_failure_data[key][0] == 1

    # 2. Deuxième échec consécutif
    auth_action._track_auth_failure(session_id, username)
    assert auth_action._auth_failure_data[key][0] == 2

    # 3. Réinitialisation après succès
    auth_action._reset_auth_failures(session_id, username)
    assert key not in auth_action._auth_failure_data


def test_is_excessive_auth_failures_time_window_expiry(auth_action, mock_settings):
    """Vérifie que le compteur de sécurité expire et se réinitialise après dépassement du TTL."""
    session_id, username = "sess_ttl", "user_ttl"
    key = f"{session_id}_{username}"

    # Simuler 3 échecs passés il y a plus de 10 minutes (au-delà des 5 minutes autorisées)
    temps_ancien = time.time() - 600
    auth_action._auth_failure_data[key] = (3, temps_ancien)

    # L'appel à l'évaluation doit nettoyer la structure expirée de manière transparente
    is_blocked = auth_action._is_excessive_auth_failures("label", session_id, username, 5.0)

    assert is_blocked is False
    assert key not in auth_action._auth_failure_data


@pytest.mark.asyncio
async def test_run_nominal_success(auth_action, dispatcher, _tracker, mock_service, mock_settings):
    """Vérifie le comportement nominal complet lorsque les identifiants sont valides."""

    # 1. Définir la structure de réponse attendue (la source de l'erreur)
    validation_response: ValidationResult = {
        "valid": True,
        "jwt": "mock_valid_jwt",
        "roles": ["student"],
        "id_user": 123,
        "full_name": "Saria Essid"
    }

    # 2. Fonction de remplacement pour le tracker
    def mocked_get_slot(key):
        if key == "last_intent":
            return ActiveIntents.RESULTS_INTENTS[0]
        elif key == "active_flow":
            return "mock_flow"
        return None

    # 3. Patchs
    with patch.object(_tracker, 'get_slot', side_effect=mocked_get_slot), \
            patch(f"{PATCH_TARGET}.fallback_credentials", return_value=("user_esprit", "pwd_esprit")), \
            patch(f"{PATCH_TARGET}.get_util_values_for_authentication", return_value="sess_01"), \
            patch(f"{PATCH_TARGET}.is_flow", return_value=True), \
            patch(f"{PATCH_TARGET}.send_invalid_format", new_callable=AsyncMock, return_value=False), \
            patch(f"{PATCH_TARGET}.validate_credentials", new_callable=AsyncMock, return_value=validation_response), \
            patch(f"{PATCH_TARGET}.get_return_slots_authentication",
                  return_value=[{"event": "slot", "name": "jwt", "value": "mock_valid_jwt"}]):

        res = await auth_action.run(dispatcher, _tracker, {})

        # 4. Assertions
        assert any(e.get("name") == "service_executed" for e in res)
        assert any(e.get("name") == "jwt" for e in res)

@pytest.mark.asyncio
async def test_run_invalid_format_blocks_auth(auth_action, dispatcher, _tracker, mock_settings):
    """Si le format est invalide, l'action doit s'arrêter avant de solliciter le backend."""

    # 1. Remplacer get_slot par un MagicMock pour permettre le side_effect
    def mocked_get_slot(key):
        if key == "last_intent":
            return ActiveIntents.RESULTS_INTENTS[0]
        return "mock_flow"

    _tracker.get_slot = MagicMock(side_effect=mocked_get_slot)

    # 2. Patch des dépendances externes
    with patch(f"{PATCH_TARGET}.fallback_credentials", return_value=("user", "pwd")), \
            patch(f"{PATCH_TARGET}.is_flow", return_value=True), \
            patch(f"{PATCH_TARGET}.send_invalid_format", new_callable=AsyncMock, return_value=True) as mock_format:
        _res = await auth_action.run(dispatcher, _tracker, {})

        # 3. Assertions
        mock_format.assert_called_once()
        assert auth_action._format_failures == 1
        assert auth_action._failed_requests == 1


@pytest.mark.asyncio
async def test_rate_limiting_excessive_failures(auth_action, dispatcher, _tracker, mock_settings):
    """Vérifie le blocage de sécurité après X tentatives erronées consécutives dans la fenêtre."""

    # 1. Remplacement de la méthode réelle par un MagicMock
    def mocked_get_slot(key):
        if key == "last_intent":
            return ActiveIntents.RESULTS_INTENTS[0]
        return "mock_flow"

    _tracker.get_slot = MagicMock(side_effect=mocked_get_slot)

    # 2. Injection nécessaire pour le dispatcher (pour éviter l'erreur sur utter_message)
    dispatcher.utter_message = MagicMock()

    session_id, username = "session_lock", "saria"

    # Injection manuelle de 3 échecs (notre limite définie dans mock_settings)
    auth_action._auth_failure_data[f"{session_id}_{username}"] = (3, time.time())

    with patch(f"{PATCH_TARGET}.fallback_credentials", return_value=(username, "wrong_pwd")), \
            patch(f"{PATCH_TARGET}.get_util_values_for_authentication", return_value=session_id), \
            patch(f"{PATCH_TARGET}.BOT_MESSAGES", {"many_attempts": "Trop de tentatives."}):
        res = await auth_action.run(dispatcher, _tracker, {})

        # Le dispatcher doit notifier l'utilisateur et l'exécution est court-circuitée
        dispatcher.utter_message.assert_called_once_with("Trop de tentatives. 5 minutes.")
        assert auth_action._auth_failures == 1
        assert res == []