"""
actions/logging/logging_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from datetime import datetime
from typing import Any, Dict
from rasa_sdk.events import SlotSet
from actions.authentication.credentials import get_user_id, decode_jwt_payload, JWTValidationError, get_jwt_remaining_time
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.FlowType import FlowType

import json
import logging
import uuid

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
    if intent == "provide_credentials":
        log.info(f"⚙️ 3 - intent = {intent}")
        for event in reversed(tracker.events):
            if event.get("event") == "user":
                last_intent = event.get("parse_data", {}).get("intent", {}).get("name")
                if last_intent != "provide_credentials":
                    log.info(f"⚙️ 4 - last_intent = {last_intent}")
                    if last_intent == ActiveIntents.ASK_RESULTAT_DISSERTATION.value:
                        language = tracker.get_slot("language")
                        log.info(f"⚙️ 5 - last_intent = {intent} - {last_intent} - {language}")
                        # 🔥 Fix here: Normalize manually
                        if language == "fr":  #if language in ["fr", "français", "francais", "française", "francaise"]:
                            return FlowType.NOTE_DISS_FR.value #"note_diss_fr"
                        elif language == "en":  #elif language in ["en", "english", "anglais", "anglaise"]:
                            return FlowType.NOTE_DISS_EN.value
                    elif last_intent ==ActiveIntents.ASK_RESULTAT_FINAL.value:
                        return FlowType.CONGRATS
                    elif last_intent == ActiveIntents.ASK_STATUS_DELIBERATION_RESULTAT.value:
                        return FlowType.DELIBERATION
    log.info("⚙️ 6 - No matching flow found, returning 'none'")
    return "none"

def get_util_values_for_semantic(tracker, action_label, question, score, best_index, active_flow, user_id, predicted_intent):
    last_question = tracker.get_slot("last_question")
    last_answer = tracker.get_slot("last_answer")
    last_intent = tracker.get_slot("last_intent")
    log_info_text("************************************************************ 🚨  " + action_label, f" : 🧠 Semantic score: {score:.2f} — best match index: {best_index}")
    log_info_text("# 👤 Current Question : ", question)
    log_info_text("# 👤 Last Question : ", last_question)
    log_info_text("# 🤖 Last Answer : ", last_answer)
    log_info_text("💥 Active Flow - SEMANTIC : ", f"{active_flow}")
    log_info_text("# 👤 ... : ", f"{user_id}")
    log_info_text("# PREDECTED Rasa intent: ", f"{predicted_intent}")


    return last_question, last_answer

def get_util_values_for_authentication(tracker, action_label):
    confidence = tracker.latest_message.get("intent", {}).get("confidence")
    active_flow = resolve_active_flow(tracker)
    intent = tracker.latest_message.get("intent", {}).get("name")
    user_input = tracker.latest_message.get("text")
    log_info_text("************************************************************ 🚨 ", f" {action_label} : {intent}")
    log_info_text("# 👤 ", user_input[:20])
    log_info_text("# Rasa intent: ", f"{intent}")
    log_info_text("# Intent confidence: ", f"{confidence}")
    log_info_text("💥 Active Flow - CREDENTIALS : ", f"{active_flow}")

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
        username = tracker.get_slot('username')
        full_name = tracker.get_slot('full_name')

        user_jwt = tracker.get_slot("jwt")
        user_roles = tracker.get_slot("roles")

        current_question = tracker.latest_message.get("text")
        last_question = tracker.get_slot("last_question") or ""
        last_answer = tracker.get_slot("last_answer") or ""

        log_action(tracker, label_action, username, full_name, user_jwt, user_roles, user_id, session_id, current_question, last_question, last_answer, confidence, active_flow, intent)

        return username, full_name, user_jwt, user_roles, user_id, session_id, current_question, last_question, last_answer, confidence, active_flow, intent
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

# Add this function to help with JWT session management
def get_jwt_session_info(tracker) -> Dict[str, Any]:
    """
    Get JWT session information for monitoring and debugging
    """
    jwt_token = tracker.get_slot("jwt")
    if not jwt_token:
        return {"has_jwt": False}

    try:
        payload = decode_jwt_payload(jwt_token)
        exp = payload.get('exp')
        remaining_time = get_jwt_remaining_time(jwt_token) if exp else None

        return {
            "has_jwt": True,
            "expires_at": datetime.fromtimestamp(exp).isoformat() if exp else None,
            "remaining_seconds": remaining_time,
            "roles": payload.get('roles', []),
            "subject": payload.get('sub')
        }
    except JWTValidationError:
        return {"has_jwt": False, "error": "invalid_token"}


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

def log_action(tracker, label_action, username, full_name, user_jwt, user_roles, user_id, session_id, current_question, last_question, last_answer, confidence, active_flow, intent):
    get_commun_logs(tracker, label_action, confidence, intent, current_question, last_question, last_answer)
    log_info_text("#💥  Active Flow : ", f"{active_flow} - {tracker.get_slot('active_flow')}")

    log_info_text("#🧍  USER - ", f"{username} : {full_name}")
    log_info_text("#🗝️  ROLE - ", f"{user_roles}")

    if user_jwt:
        log_info_text("#🗝️  JWTo - ", f"{user_jwt[:20]} ... {user_jwt[-20:]}")
        log_info_text("#🌐  Browser IDS - ", f"{user_id} ... {session_id}")

    log_info_text("\n", "")

def log_response_payload(action_label: str, status: int, payload: Any):
    log.info(f"🚩  🚩  🚩    {action_label} {status} -> {json.dumps(payload, ensure_ascii=False)}")

def log_info_text(action_label: str, message: str):
    log.info(f"ℹ️    {action_label} -> {message}")

def log_info_auth(action_label: str, user_roles, user_jwt: str):
    log.info(f"🔐   {action_label} -> Roles = {user_roles}\n JWT extracted for user : {user_jwt[20:]} ... {user_jwt[-20:]}")

def log_info_expected_flow(action_label: str, message):
    log.info(f"ℹ️    {action_label} -> Expected FLOW : {message}")

def log_warn_text(action_label: str, message: str):
    log.warning(f"⚠️    {action_label} -> {message}")

def log_debug_text(action_label: str, message: str):
    log.debug(f"🐞   {action_label} -> {message}")

def log_error_text(action_label: str, error):
    log.error(f"❌   {action_label} -> {error}")

def log_exception_text(action_label: str, error):
    log.exception(f"🚨   {action_label} -> {error}")