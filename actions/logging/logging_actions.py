"""
actions/logging/logging_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import secrets
from typing import Text
from typing import TypeVar
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.Constants import BOT_MESSAGES
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_with_log, get_user_id
from actions.utils.error_handling import handle_action_errors
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import alert_technical_problem_exception, send_fallback_warning_to_dsi_forwarded_by_buttons
from actions.utils.slots_helpers import empty_slots

import json
import logging
import uuid

log = logging.getLogger("rasa-actions")
ServiceType = TypeVar('ServiceType', bound='IResultsService')
T = TypeVar('T', bound='IResultsService')

class ActionSetSession(Action):
    def __init__(self, session_service: IResultsService):
        self.session_service = session_service

    def name(self):
        return ActionsNome.ACTION_SET_SESSION.value

    @handle_action_errors
    async def run(self, dispatcher, tracker, domain):
        session_id = tracker.get_slot("session_id")
        log.info(f"ℹ️  action_set_session : {session_id}")

        if session_id is None:
            session_id = str(uuid.uuid4())
            log.info(f"ℹ️  action_set_session : {session_id}")
            return [SlotSet("session_id", session_id), SlotSet("active_flow", "none")]

        return empty_slots()


class ActionSetUser(Action):
    def __init__(self, user_service: IResultsService):
        self.user_service = user_service

    def name(self):
        return ActionsNome.ACTION_SET_USER.value

    @handle_action_errors
    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.sender_id
        log.info(f"ℹ️  action_set_user : {user_id}")

        if user_id is None:
            user_id = get_user_id(tracker)
            log.info(f"ℹ️  action_set_user : {user_id}")
            return [SlotSet("user_id", user_id), SlotSet("active_flow", "none")]

        return empty_slots()


class ActionLogFeedback(Action):
    def __init__(self, feedback_service: IResultsService):
        self.feedback_service = feedback_service

    def name(self) -> Text:
        return ActionsNome.ACTION_LOG_FEEDBACK.value

    @handle_action_errors
    async def run(self, dispatcher, tracker, domain):

        action_label = ActionsLabel.PY_LOGGING.value
        full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        # Get last Q/A + vote
        vote = "utile" if intent == "affirm_helpful" else "inutile"

        payload = {
            "question": question,
            "answer": answer,
            "vote": vote,
            "intent": tracker.get_slot("predicted_intent") or intent,
            "userId": user_id,
            "sessionId": session_id
        }

        try:
            possible_faqs = await self.feedback_service.save_feedback(payload)
            # log_info_text(action_label, f"ℹ️  possible_faqs : {possible_faqs}")

            # If it's a JSON string, load it
            if isinstance(possible_faqs, str):
                possible_faqs = json.loads(possible_faqs)

            # 👉 Fetch response from DB
            user_input_clean = (user_input or "").lower().strip()

            # Try exact match first
            reply = None
            for faq in possible_faqs:
                if faq.get('userInput').lower().strip() == user_input_clean:
                    answer = faq.get('botResponse')
                    reply = answer.replace("\\n", "\n")
                    break

            # If no exact match, pick random variation
            if not reply and possible_faqs:
                reply = secrets.choice(possible_faqs).get('botResponse')

            lines = reply.split('\n')
            for lin in lines:
                dispatcher.utter_message(text=lin or BOT_MESSAGES.get('thanks_for_your_feedback'))

            bot_response_text = lines

        except Exception as e:
            send_fallback_warning_to_dsi_forwarded_by_buttons(dispatcher)
            bot_response_text = alert_technical_problem_exception(action_label, e)

        await log_chat(user_id, session_id, user_input, bot_response_text, intent, confidence)
        return [SlotSet("active_flow", active_flow)]
