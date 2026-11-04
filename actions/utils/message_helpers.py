"""
actions/utils/message_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import logging
from typing import Text, List, Optional, Dict

from actions.actions import get_random_message
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS
from actions.logging.logger import notify_team_leader_by_technical_problem
from actions.settings.settings import settings
from actions.utils.messages_dispatcher import MessageDispatcher

log = logging.getLogger("rasa-actions")

##### Send standard fallback problem to team leader with buttons
standard_user_friendly_msg = get_random_message(BOT_MESSAGES['fallback_dsi'])

async def send_notif_with_btn(action_label, message, exception, payload):
    payload = update_payload(action_label, message, exception, payload)
    await notify_team_leader_by_technical_problem(payload)

async def send_custom_fallback_problem_to_team_leader_with_fe_btn(dispatcher, action_label, payload, code_exception, user_friendly_msg, buttons):
    """1. Pick a custom message from a list
       2. Notify Team Leader
       3. Alert Payload"""
    await send_notif_with_btn(action_label, user_friendly_msg, code_exception, payload)
    send_multiple_messages_forwarded_by_buttons(dispatcher, user_friendly_msg, buttons)
    return user_friendly_msg

async def send_custom_fallback_problem_to_team_leader_with_fe(dispatcher, action_label, payload, code_exception, user_friendly_msg):
    """1. Pick a custom message from a list
       2. Notify Team Leader
       3. Alert Payload"""
    await send_notif_with_btn(action_label, user_friendly_msg, code_exception, payload)
    send_multiple_messages_forwarded_by_buttons(dispatcher, user_friendly_msg, FEEDBACK_BUTTONS)
    return user_friendly_msg

async def send_standard_fallback_problem_to_team_leader_with_fe(dispatcher, action_label, payload, code_exception):
    """1. Pick a random message from a list
       2. Notify Team Leader
       3. Alert Payload"""
    await send_notif_with_btn(action_label, standard_user_friendly_msg, code_exception, payload)
    send_multiple_messages_forwarded_by_buttons(dispatcher, standard_user_friendly_msg, FEEDBACK_BUTTONS)
    return standard_user_friendly_msg

async def send_standard_fallback_problem_to_team_leader(action_label, payload, code_exception):
    """1. Pick a random message from a list
       2. Notify Team Leader
       3. Alert Payload"""
    await send_notif_with_btn(action_label, standard_user_friendly_msg, code_exception, payload)
    return standard_user_friendly_msg

########################################################################################################################
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

def update_payload(action_label, message, exception, payload):
    # append answer
    answer = f"<br/>{BOT_MESSAGES.get('technical_problem_exception')} {action_label} : <br/>{message} => <br/>{exception}"
    log.exception(message)

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
    if len(question.split()) > settings.MAX_USER_QUESTION_WORDS:
        dispatcher.utter_message(BOT_MESSAGES.get('skip_long_question'))
        return True
    return False

def adjust_lines(message):
    return message