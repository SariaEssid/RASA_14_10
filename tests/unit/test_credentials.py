"""
tests/unit/test_credentials.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

# Target imports under test
from actions.authentication.credentials import (
    extract_credentials,
    ensure_credentials,
    fallback_credentials,
    is_flow,
    success_authentication,
    send_invalid_format,
    fail_authentication_dispatcher,
    InvalidCredentialsError,
    validate_credentials,
    get_user_id,
    generate_anonymous_id,
    hash_sha256,
    log_authentication
)

PATCH_TARGET = "actions.authentication.credentials"


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def dispatcher() -> CollectingDispatcher:
    return CollectingDispatcher()


@pytest.fixture
def tracker() -> MagicMock:
    tracker_mock = MagicMock(spec=Tracker)
    tracker_mock.sender_id = "student_saria"
    tracker_mock.latest_message = {
        "text": "My username is saria.essid and password=SecretPass!",
        "intent": {"name": "provide_credentials", "confidence": 0.98},
        "metadata": {}
    }
    tracker_mock.get_intent_of_latest_message = MagicMock(return_value="provide_credentials")

    # Base dictionary fallback implementation for slot configurations
    slots = {
        "username": None,
        "password": None,
        "active_flow": "auth_flow",
        "session_id": "session_abc123",
        "user_id": None
    }
    tracker_mock.get_slot = MagicMock(side_effect=lambda key: slots.get(key))
    # Allow test manipulation easily by attached reference dictionary
    tracker_mock._test_slots = slots
    return tracker_mock


# ==============================================================================
# 1. CREDENTIAL EXTRACTION ENGINE TESTS
# ==============================================================================

@pytest.mark.parametrize("input_text,expected", [
    ("identifiant: saria.essid mdp: MyPassword123", {"username": "saria.essid", "password": "MyPassword123"}),
    ("login=admin pass=root", {"username": "admin", "password": "root"}),
    ("nom d'utilisateur: test_user\n mot de passe: special#pass",
     {"username": "test_user", "password": "special#pass"}),
    ("plain text without match patterns", {}),
])
def test_extract_credentials_variants(input_text, expected):
    assert extract_credentials(input_text) == expected


def test_extract_credentials_exception_handling():
    with patch("re.search", side_effect=Exception("Regex breakdown engine failure")):
        # Ensure it safely catches inside loop, prints logs, and returns empty dict gracefully
        assert extract_credentials("user: saria") == {}


def test_ensure_credentials_slots_empty(tracker):
    text = "username: saria_dev password: Password123"
    username, password = ensure_credentials(tracker, text)
    assert username == "saria_dev"
    assert password == "Password123"


def test_ensure_credentials_slots_filled(tracker):
    tracker._test_slots["username"] = "pre_filled_user"
    tracker._test_slots["password"] = "pre_filled_pass"
    username, password = ensure_credentials(tracker, "username: override password: dummy")
    assert username == "pre_filled_user"
    assert password == "pre_filled_pass"


def test_fallback_credentials_trigger_path(tracker):
    text = "login: fallback_user mdp: fallback_pass"
    username, password = fallback_credentials(tracker, text)
    assert username == "fallback_user"
    assert password == "fallback_pass"


# ==============================================================================
# 2. FLOW UTILITIES & DISPATCHER ACTIONS
# ==============================================================================

def test_is_flow_matching_and_mismatching(tracker):
    assert is_flow(tracker, "auth_flow") is True
    assert is_flow(tracker, "different_flow") is False


def test_success_authentication_formatting():
    msg = success_authentication("Saria Essid")
    assert "Saria Essid" in msg


@pytest.mark.asyncio
async def test_send_invalid_format_conditions(dispatcher, tracker):
    # Condition A: Username is None
    assert await send_invalid_format(dispatcher, tracker, None, "pass123") is True

    # Condition B: Username equals specific placeholder edgecase 'est'
    assert await send_invalid_format(dispatcher, tracker, "est", "pass123") is True

    # Condition C: Valid values
    assert await send_invalid_format(dispatcher, tracker, "valid_user", "valid_pass") is False


def test_fail_authentication_dispatcher(dispatcher, tracker):
    with patch(f"{PATCH_TARGET}.log_authentication") as mock_log_auth:
        fail_authentication_dispatcher(dispatcher, tracker)
        assert len(dispatcher.messages) == 1
        mock_log_auth.assert_called_once()


# ==============================================================================
# 3. CORE VALIDATION ROUTINE & CIRCUIT BREAKER TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_validate_credentials_success(dispatcher, tracker):
    async def mock_verify_success(_payload):
        return {"fullNameUser": "Saria Essid", "jwt": "mock_valid_token", "idUser": "usr_99", "roles": ["ADMIN"]}

    with patch(f"{PATCH_TARGET}.validate_jwt_before_use", return_value=True):
        result = await validate_credentials(
            dispatcher, tracker, "saria", "secret", mock_verify_success, "action_login"
        )
        assert result["valid"] is True
        assert result["full_name"] == "Saria Essid"
        assert result["id_user"] == "usr_99"


@pytest.mark.asyncio
async def test_validate_credentials_invalid_jwt_response(dispatcher, tracker):
    async def mock_verify_success(_payload):
        return {"fullNameUser": "Saria Essid", "jwt": "mock_expired_token", "idUser": "usr_99"}

    with patch(f"{PATCH_TARGET}.validate_jwt_before_use", return_value=False):
        result = await validate_credentials(
            dispatcher, tracker, "saria", "secret", mock_verify_success, "action_login"
        )
        assert result["valid"] is False
        assert result["error_type"] == "invalid_token"


@pytest.mark.asyncio
async def test_validate_credentials_invalid_auth_exception(dispatcher, tracker):
    async def mock_verify_fail(_payload):
        raise InvalidCredentialsError("Unauthorized access code 401")

    result = await validate_credentials(
        dispatcher, tracker, "saria", "wrong", mock_verify_fail, "action_login"
    )
    assert result["valid"] is False
    assert result["error_type"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_validate_credentials_circuit_breaker_open(dispatcher, tracker):
    async def mock_verify_circuit(_payload):
        # Pass dummy string pattern description requirement to initialize CircuitBreakerError
        raise CircuitBreakerError(MagicMock(), "Circuit opened dynamically")

    result = await validate_credentials(
        dispatcher, tracker, "saria", "secret", mock_verify_circuit, "action_login"
    )
    assert result["valid"] is False
    assert result["error_type"] == "circuit_open"


@pytest.mark.asyncio
async def test_validate_credentials_generic_exception(dispatcher, tracker):
    async def mock_verify_crash(_payload):
        raise RuntimeError("Database connection timed out drop connection")

    with patch(f"{PATCH_TARGET}.alert_technical_problem_exception") as mock_alert, \
            patch(f"{PATCH_TARGET}.send_fallback_problem_to_dsi_forwarded_by_buttons") as mock_dsi:
        result = await validate_credentials(
            dispatcher, tracker, "saria", "secret", mock_verify_crash, "action_login"
        )
        assert result["valid"] is False
        assert result["error_type"] == "exception"
        mock_alert.assert_called_once()
        mock_dsi.assert_called_once()


# ==============================================================================
# 4. IDENTIFICATION ENGINE & ANONYMIZATION STRATEGY
# ==============================================================================

def test_get_user_id_resolution_chains(tracker):
    # Chain Level 1: Authenticated target slot exists
    tracker._test_slots["user_id"] = "auth_fixed_id"
    assert get_user_id(tracker) == "auth_fixed_id"

    # Chain Level 2: Platform ID string matching pattern
    tracker._test_slots["user_id"] = None
    tracker.sender_id = "saria.essid@esprit.tn"
    assert get_user_id(tracker) == "saria.essid@esprit.tn"

    # Chain Level 3: Fallback resolution triggers fingerprint calculations
    tracker.sender_id = "student_saria"
    tracker.latest_message["metadata"] = {"fingerprint": "device_hash_xyz"}
    assert get_user_id(tracker).startswith("fp_")


def test_generate_anonymous_id_metadata_combinations(tracker):
    # Scenario A: Fingerprint matching metadata mapping rules
    tracker.latest_message["metadata"] = {"fingerprint": "browser_canvas_fp"}
    id_fp = generate_anonymous_id(tracker)
    assert id_fp.startswith("fp_")

    # Scenario B: Salted IP address + User-Agent calculation logic
    tracker.latest_message["metadata"] = {"ip": "192.168.1.100", "user_agent": "Mozilla/Chrome"}
    id_ipua = generate_anonymous_id(tracker)
    assert id_ipua.startswith("ipua_")

    # Scenario C: Clean fallback using secure native implementation string values
    tracker.latest_message["metadata"] = {}
    id_fallback = generate_anonymous_id(tracker)
    assert id_fallback.startswith("fallback_")


def test_hash_sha256_truncation_limits():
    hashed = hash_sha256("identity_anonymization_layer_test")
    assert len(hashed) == 16

@pytest.mark.asyncio
async def test_log_authentication(tracker):
    # Patch log_chat directly as an AsyncMock to handle the new async/await cycle cleanly
    with patch(f"{PATCH_TARGET}.log_chat", new_callable=AsyncMock) as mock_log_chat:
        await log_authentication(tracker, "User authentication verified")
        mock_log_chat.assert_called_once()