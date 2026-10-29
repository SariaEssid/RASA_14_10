"""
actions/logging/logging_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import hashlib
import json
import logging
import uuid
from typing import Any

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet

from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.FlowType import FlowType
from actions.settings.settings import settings

log = logging.getLogger("rasa-actions")

def generate_session_id():
    session_id = str(uuid.uuid4())
    return str(uuid.uuid4()), SlotSet("session_id", session_id)

def generate_user_id(tracker):
    user_id = get_user_id(tracker)
    return get_user_id(tracker), SlotSet("user_id", user_id)

def resolve_active_flow(tracker):
    if flow := tracker.get_slot("active_flow"):
        log.info(f"⚙️ 1 - active_flow = {flow}")
        return flow

    intent = tracker.latest_message.get("intent", {}).get("name")
    log.info(f"⚙️ 2 - intent = {intent}")
    log.info("⚙️ 6 - No matching flow found, returning 'none'")
    return "none"

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

def get_util_values_for_semantic(tracker, action_label, question, score, best_index, active_flow, user_id, predicted_intent):
    last_question = tracker.get_slot("last_question")
    last_answer = tracker.get_slot("last_answer")
    log_info_text("************************************************************ 🚨  " + action_label, f" : 🧠 Semantic score: {score:.2f} — best match index: {best_index}")
    log_info_text("# 👤 Current Question : ", question)
    log_info_text("# 👤 Last Question : ", last_question)
    log_info_text("# 🤖 Last Answer : ", last_answer)
    log_info_text("💥 Active Flow - SEMANTIC : ", f"{active_flow}")
    log_info_text("# 👤 ... : ", f"{user_id}")
    log_info_text("# PREDECTED Rasa intent: ", f"{predicted_intent}")


    return last_question, last_answer


def get_last_conversation(tracker, action_label):
    last_last_question = tracker.get_slot("last_question") or "" # 17-06-2026
    last_answer = tracker.get_slot("last_answer")

    log_info_text(action_label, "last_conversation Q : " + last_last_question)

    if last_answer:
        log_info_text(action_label, "last_conversation A : " + last_answer)
    return last_last_question, last_answer

def get_current_intent(tracker):
    return tracker.latest_message.get("intent", {}).get("name")

def get_last_last_question(tracker):
    return tracker.get_slot("last_question") or ""

def get_last_last_answer(tracker):
    return tracker.get_slot("last_answer") or ""

def get_util_minimal_values_with_log(tracker, label_action):
    try:
        session_id, user_id, confidence = get_user_session_conf_values(tracker)
        intent = tracker.latest_message.get("intent", {}).get("name")

        current_question = tracker.latest_message.get("text")
        last_question = tracker.get_slot("last_question") or ""
        last_answer = tracker.get_slot("last_answer") or ""

        log_action_minimal(tracker, label_action, user_id, session_id, confidence, intent, current_question, last_question, last_answer)

        return user_id, session_id, confidence, intent
    except Exception as e:
        log.error(f"🚨  Error in getUtilValues: {e}")
        return None

def get_util_values_with_log(tracker, label_action):
    try:
        session_id, user_id, confidence = get_user_session_conf_values(tracker)
        active_flow = resolve_active_flow(tracker)
        intent = tracker.latest_message.get("intent", {}).get("name")
        full_name = tracker.get_slot('full_name')
        user_roles = tracker.get_slot("roles")
        current_question = tracker.latest_message.get("text")
        last_question = tracker.get_slot("last_question") or ""
        last_answer = tracker.get_slot("last_answer") or ""

        log_action(tracker, label_action, full_name, user_roles, user_id, session_id, current_question, last_question, last_answer, confidence, active_flow, intent)

        return full_name, user_roles, user_id, session_id, current_question, last_question, last_answer, confidence, active_flow, intent
    except Exception as e:
        log.error(f"🚨  Error in getUtilValues: {e}")
        return None

def get_util_values_for_error_handling(tracker):
    try:
        session_id, user_id, confidence = get_user_session_conf_values(tracker)
        intent = tracker.latest_message.get("intent", {}).get("name")
        user_input = tracker.latest_message.get("text")
        return user_id, session_id, user_input, intent, confidence
    except Exception as e:
        log.error(f"🚨  Error in getUtilValues: {e}")
        return None


def get_user_session_conf_values(tracker):
    session_id = tracker.get_slot("session_id")
    user_id = tracker.get_slot("user_id") or tracker.sender_id

    log.info(f"🏁 1 : session_id | user_id = {session_id} | {user_id}")

    if session_id is None:
        # Generate new session ID logic
        session_id, slot_set_event = generate_session_id()
        log.info(f"🏁 2 : session_id = {session_id}")

    if user_id is None:
        # Generate new session ID logic
        user_id, slot_set_event = generate_user_id(tracker)
        log.info(f"🏁 3 : user_id = {user_id}")

    user_id = tracker.sender_id
    confidence = tracker.latest_message.get("intent", {}).get("confidence")
    return session_id, user_id, confidence

def get_commun_logs(tracker, label_action, confidence, intent, current_question, last_question, last_answer):
    log_info_text("\n\n************************************************************", f" 🚨  {label_action} : {intent} ***")
    log_info_text("# 👤 ", current_question[:20])
    log_info_text("# LAST 👤 : ", last_question[:20])
    log_info_text("# LAST 🤖 : ", last_answer[:20])

    last_intent = tracker.get_slot('last_intent')
    if last_intent:
        log_info_text("# Rasa last-intent / intent: ", f"{last_intent} - {intent}")
    else:
        log_info_text("# Intent: ", f"{tracker.get_intent_of_latest_message()}")

    log_info_text("# Intent confidence: ", f"{confidence}")

def log_action_minimal(tracker, label_action, user_id, session_id, confidence, intent, current_question, last_question, last_answer):
    get_commun_logs(tracker, label_action, confidence, intent, current_question, last_question, last_answer)
    log_info_text("#🌐  Browser IDS - ", f"{user_id} ... {session_id}\n")

def log_action(tracker, label_action, full_name, user_roles, user_id, session_id, current_question, last_question, last_answer, confidence, active_flow, intent):
    get_commun_logs(tracker, label_action, confidence, intent, current_question, last_question, last_answer)
    log_info_text("#💥  Active Flow : ", f"{active_flow} - {tracker.get_slot('active_flow')}")

    if tracker.get_slot("full_name"):
        log_info_text("#🧍  USER - full_name : ", f"{full_name}")

    log_info_text("#🗝️  ROLE - ", f"{user_roles}")

    log_info_text("#🌐  Browser IDS - ", f"{user_id} ... {session_id}")


    log_info_text("\n", "")

def log_response_payload(action_label: str, status: int, payload: Any):
    log.info(f"🚩  🚩  🚩    {action_label} {status} -> {json.dumps(payload, ensure_ascii=False)}")

def log_info_text(action_label: str, message: str):
    log.info(f"ℹ️    {action_label} -> {message}")

def log_warn_text(action_label: str, message: str):
    log.warning(f"⚠️    {action_label} -> {message}")

def log_debug_text(action_label: str, message: str):
    log.debug(f"🐞   {action_label} -> {message}")

def log_error_text(action_label: str, error):
    log.error(f"❌   {action_label} -> {error}")

def log_exception_text(action_label: str, error):
    log.exception(f"🚨   {action_label} -> {error}")