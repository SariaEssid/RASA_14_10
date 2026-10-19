"""
actions/utils/message_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import secrets
from typing import Text, List, Optional, Dict
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS
from actions.logging.logger import notify_team_leader_by_technical_problem
from actions.settings.settings import settings
from actions.utils.messages_dispatcher import MessageDispatcher

import logging

log = logging.getLogger("rasa-actions")
_SENSITIVE_KEYS = {"password", "mdp", "pass", "jwt", "token", "authorization"}

def send_multiple_messages(dispatcher, reply: Text):
    """Legacy function - delegate to MessageDispatcher"""
    MessageDispatcher.send_secure(dispatcher, reply, with_buttons=False)

def send_message_forwarded_by_buttons(dispatcher, answer: Text):
    """Legacy function - delegate to MessageDispatcher"""
    MessageDispatcher.send_secure(dispatcher, answer, with_buttons=True)

def send_multiple_messages_forwarded_by_buttons(dispatcher, answer: Text, buttons: Optional[List[Dict]]):
    """Legacy function - delegate to MessageDispatcher"""
    MessageDispatcher.send_secure(
        dispatcher=dispatcher,
        message=answer,
        with_buttons=True,
        buttons=buttons
    )

def send_multiple_messages_images_forwarded_by_buttons(dispatcher, answer: Text, images: List[Text], buttons: Optional[List[Dict]], post_fix_msg: Optional[Text] = None):
    """Legacy function - delegate to MessageDispatcher"""
    MessageDispatcher.send_secure(
        dispatcher=dispatcher,
        message=answer,
        with_buttons=True,
        buttons=buttons,
        with_images=True,
        images=images,
        post_fix_msg=post_fix_msg
    )

def send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload, exception):
    return send_random_message_with_alter_for_dsi(dispatcher, BOT_MESSAGES['fallback_dsi'], action_label, payload, exception)

def send_custom_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload, exception, message, buttons):
    return send_exception_message(dispatcher, action_label, payload, exception, message, buttons)

def send_fallback_warning_to_dsi_forwarded_by_buttons(dispatcher):
    send_custom_message(dispatcher, 'unsaved_fallback')

def original_alert_affirm_without_discussion():
    return BOT_MESSAGES.get('affirm_no_result') # affirm_without_discussion

def original_alert_unexpected_response():
    return BOT_MESSAGES.get('unexpected_response')

def original_alert_follow_my_proposition():
    return BOT_MESSAGES.get('follow_my_proposition')

def alert_technical_problem_error(action_label, message):
    answer = f"{BOT_MESSAGES.get('technical_problem_error')} {action_label} : {message}"
    log.error(answer)
    return answer

def alert_technical_problem_exception(action_label, exception):
    answer = f"{BOT_MESSAGES.get('technical_problem_exception')} {action_label} : {exception}"
    log.exception(answer)
    return answer

def send_random_message_with_alter_for_dsi(dispatcher, message_list, action_label, payload, exception):
    """1. Pick a random message from a list
       2. Notify Team Leader
       3. Alert User"""
    formed_msg = get_random_message(message_list)

    payload = update_payload(action_label, formed_msg, exception, payload)
    notify_team_leader_by_technical_problem(payload)

    # send dispatcher
    send_multiple_messages_forwarded_by_buttons(dispatcher, formed_msg, FEEDBACK_BUTTONS)
    return formed_msg

def send_random_message_user_and_dsi(action_label, payload, exception):
    """1. Pick a random message from a list
       2. Notify Team Leader
       3. Alert User"""
    formed_msg = get_random_message(BOT_MESSAGES['fallback_dsi'])

    payload = update_payload(action_label, formed_msg, exception, payload)
    notify_team_leader_by_technical_problem(payload)

    return formed_msg

def get_random_message(message_list):
    message = secrets.choice(message_list)
    formed_msg = adjust_lines(message)
    return formed_msg

def send_exception_message(dispatcher, action_label, payload, exception, message, buttons):
    """1. Pick a random message from a list
       2. Notify Team Leader
       3. Alert User"""

    payload = update_payload(action_label, message, exception, payload)
    notify_team_leader_by_technical_problem(payload)

    # send dispatcher
    send_multiple_messages_forwarded_by_buttons(dispatcher, message, buttons)
    return message

def update_payload(action_label, message, exception, payload):
    # append answer
    answer = f"<br/>{BOT_MESSAGES.get('technical_problem_exception')} {action_label} : <br/>{message} => <br/>{exception}"
    log.exception(message)

    # omit sensitive data
    payload = {k: v for k, v in payload.items()
               if k.lower() not in _SENSITIVE_KEYS}

    # integrate botReply to payload and notify team leader with API
    payload["botReply"] = answer

    return payload

def send_custom_message(dispatcher, message_key):
    """Send a message by key"""
    message = BOT_MESSAGES.get(message_key, "")
    if not message:
        log.warning(f"Message key '{message_key}' not found in MESSAGES.")
    send_multiple_messages_forwarded_by_buttons(dispatcher, adjust_lines(message), FEEDBACK_BUTTONS)

def exit_for_empty_and_long_question(dispatcher, question) -> bool:
    if not question or len(question) < 3:
        dispatcher.utter_message(BOT_MESSAGES.get('skip_little_question'))
        return True
    if len(question) > settings.MAX_USER_QUESTION_WORDS:
        dispatcher.utter_message(BOT_MESSAGES.get('skip_long_question'))
        return True
    return False

def adjust_lines(answer):
    return answer.replace("\\n", "\n")