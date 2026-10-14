"""
actions/authentication/credentials.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from datetime import datetime
from typing import Any, Text, Dict, Optional
from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS
from actions.logging.logger import log_chat
from actions.settings.settings import settings
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons, \
    alert_technical_problem_exception, send_fallback_problem_to_dsi_forwarded_by_buttons

import hashlib
import logging
import re
import time
import uuid
import jwt

log = logging.getLogger("rasa-actions")

def extract_credentials(text: Text) -> Dict[Text, Text]:
    """Military-grade credential extraction"""
    patterns = {
        'username': [
            # English/French patterns with robust separators
            r'(?:username|user|login|id|identifiant|nom\s*d[\']?utilisateur)\s*[=:;,\s]\s*([^\s;,]*)',
            r'(?:user|id)\s*[:=]\s*([^\s;]+)'
        ],
        'password': [
            # Capture EVERYTHING after password label (including special chars)
            r'(?:password|pass|mdp|mot\s*de\s*passe|code)\s*[=:;]\s*([^\n]*)',
            # Alternative pattern for tight spaces
            r'(?:pass|mdp)[^\w]*([^\s]+)'
        ]
    }

    credentials = {}
    for cred_type, regex_list in patterns.items():
        for pattern in regex_list:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and match.group(1):
                    # Clean but preserve ALL special characters
                    clean_val = match.group(1).strip().strip('"\'')
                    if clean_val:  # Only store if we found something
                        credentials[cred_type] = clean_val
                        break
            except Exception as e:
                log.error(f"🚨  NO 1 : EXCEPTION => {e}")
                continue
    return credentials

def ensure_credentials(tracker, text):
    username = tracker.get_slot("username")
    password = tracker.get_slot("password")
    if not username or not password:
        creds = extract_credentials(text)
        username = creds.get("username", username)
        password = creds.get("password", password)
    return username, password

def fallback_credentials(tracker, text):
    username = tracker.get_slot("username")
    password = tracker.get_slot("password")
    if not username or not password:
        log.error(f"🚨  NO-1 : username={username} - password={password} : not username or not password")
        username, password = ensure_credentials(tracker, text)
    return username, password

def is_flow(tracker, expected_flow):
    log.info("AZERTY-111: " + expected_flow)

    if tracker.get_slot("active_flow"):
        log.info("AZERTY-222: " + tracker.get_slot("active_flow"))

    return tracker.get_slot("active_flow") == expected_flow

def success_authentication(full_name):
    msg_success_auth = BOT_MESSAGES.get('credentials_valid_format')
    msg_success_auth += f"👤Vous êtes {full_name},\n"
    return msg_success_auth

async def send_invalid_format(dispatcher: CollectingDispatcher, tracker: Tracker, username: Optional[Text], password: Optional[Text]) -> bool:
    """Show format error and return True if format is invalid"""
    if not username or not password or username.strip() == "est":
        msg = BOT_MESSAGES.get('credentials_invalid_format')
        send_multiple_messages_forwarded_by_buttons(dispatcher, msg, FEEDBACK_BUTTONS)
        await log_chat(
            tracker.sender_id,
            tracker.get_slot("session_id"),
            tracker.latest_message.get("text"),
            msg,
            tracker.get_intent_of_latest_message(),
            tracker.latest_message.get("intent", {}).get("confidence")
        )
        return True
    return False

def fail_authentication_dispatcher(
        dispatcher: CollectingDispatcher,
        tracker: Tracker
) -> None:
    """Handle failed authentication for valid-formatted credentials"""
    answer = BOT_MESSAGES.get('failed_auth')
    dispatcher.utter_message(text=answer)
    log_authentication(tracker, answer)

# 1️⃣ Define a custom exception for invalid credentials
class InvalidCredentialsError(Exception):
    pass

async def validate_credentials(
    dispatcher, tracker, username: Text, password: Text, verify_fn: callable, action_label: Text
) -> Dict[str, Any]:
    payload = {"username": username.strip(), "password": password.strip()}

    try:
        # ✅ Circuit automatically tracks failures
        response = await verify_fn(payload)

        # Successful login
        full_name = response["fullNameUser"]
        jwt_token = response["jwt"]

        # Validate the JWT we received from Spring Boot
        if not validate_jwt_before_use(jwt_token):
            log.error("Received expired JWT token from authentication service")
            dispatcher.utter_message("🔐 Session invalide reçue du serveur. Veuillez réessayer.")
            return {
                "valid": False,
                "username": username,
                "password": password,
                "error_type": "invalid_token"
            }

        dispatcher.utter_message(f"{BOT_MESSAGES.get('success_auth')} {full_name}")
        return {
            "valid": True,
            "full_name": full_name,
            "id_user": response["idUser"],
            "username": username,
            "password": password,
            "jwt": jwt_token,
            "roles": response.get("roles", [])
        }

    except InvalidCredentialsError:
        # ❌ Do NOT count 401 as a failure in the circuit
        fail_authentication_dispatcher(dispatcher, tracker)
        return {"valid": False, "username": username, "password": password, "error_type": "invalid_credentials"}

    except CircuitBreakerError:
        # Circuit is OPEN due to real failures (network/server)
        message_auth = BOT_MESSAGES.get('circuit_opened_alert')
        dispatcher.utter_message(message_auth)
        return {"valid": False, "username": username, "password": password, "error_type": "circuit_open"}

    except Exception as e:
        alert_technical_problem_exception(dispatcher, {str(e)})
        send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload, FEEDBACK_BUTTONS)
        return {"valid": False, "username": username, "password": password, "error_type": "exception"}

def get_user_id(tracker) -> str:
    """Resolve persistent user ID with fallbacks."""
    # 1. Check authenticated user slot
    if user_id := tracker.get_slot("user_id"):
        return user_id

    # 2. Use platform ID (Facebook/Telegram/etc)
    if "@" in tracker.sender_id:
        return tracker.sender_id

    # 3. Fallback to fingerprint and cookie
    return generate_anonymous_id(tracker)

def generate_anonymous_id(tracker: Tracker) -> str:
    """
    Generates a persistent but non-PII anonymous user ID using:
    1. Browser fingerprint (if available)
    2. Fallback to salted IP + User-Agent hash
    3. Ultimate fallback to UUID
    """
    # Try browser fingerprint first (requires JS to frontend)
    if fingerprint := tracker.latest_message.get("metadata", {}).get("fingerprint"):
        return f"fp_{hash_sha256(fingerprint)}"

    # Fallback: IP + User-Agent hash (salted for privacy)
    ip = tracker.latest_message.get("metadata", {}).get("ip", "")
    user_agent = tracker.latest_message.get("metadata", {}).get("user_agent", "")
    if ip and user_agent:
        salt = settings.ANONYMIZATION_SALT
        return f"ipua_{hash_sha256(f'{salt}{ip}{user_agent}')}"

    # Ultimate fallback (least persistent)
    return f"fallback_{str(uuid.uuid4())}"

def hash_sha256(data: str) -> str:
    """Helper for consistent hashing"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]  # 16 chars for readability

async def log_authentication(tracker, message_auth):
    await log_chat(
        tracker.sender_id,
        tracker.get_slot("session_id"),
        tracker.latest_message.get("text"),
        message_auth,
        tracker.get_intent_of_latest_message(),
        tracker.latest_message.get("intent", {}).get("confidence")
    )


class JWTValidationError(Exception):
    """Custom exception for JWT validation failures"""
    pass


def decode_jwt_payload(token: str) -> dict:
    """
    Safely decode JWT without verification to check expiration
    This is READ-ONLY - we're not validating signatures, just reading expiration
    """
    try:
        # Decode without verification to read payload (safe for expiration checks)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except jwt.DecodeError as e:
        log.error(f"JWT decode error: {e}")
        raise JWTValidationError("Invalid token format")
    except Exception as e:
        log.error(f"Unexpected JWT error: {e}")
        raise JWTValidationError("Token validation failed")


def is_jwt_expired(token: str, leeway_seconds: int = 30) -> bool:
    """
    Check if JWT token is expired with optional leeway for clock skew
    This prevents using expired tokens for API calls
    """
    try:
        payload = decode_jwt_payload(token)

        # Check expiration time
        exp = payload.get('exp')
        if not exp:
            log.warning("JWT has no expiration claim - treating as valid")
            return False  # No expiration claim, assume valid

        current_time = time.time()
        is_expired = current_time > (exp + leeway_seconds)

        if is_expired:
            log.warning(f"JWT expired at {datetime.fromtimestamp(exp)}")

        return is_expired

    except JWTValidationError:
        return True  # Treat invalid tokens as expired


def get_jwt_remaining_time(token: str) -> Optional[float]:
    """
    Get remaining time in seconds until JWT expires
    Useful for session management
    """
    try:
        payload = decode_jwt_payload(token)
        exp = payload.get('exp')
        if not exp:
            return None

        remaining = exp - time.time()
        return max(0, remaining)  # Return 0 if already expired

    except JWTValidationError:
        return 0


def validate_jwt_before_use(token: str) -> bool:
    """
    Main validation function to check JWT before making API calls
    Returns True if token is valid and not expired
    """
    if not token:
        log.error("Empty JWT token provided")
        return False

    if is_jwt_expired(token):
        log.error("JWT token is expired")
        return False

    log.debug("JWT token validation successful")
    return True