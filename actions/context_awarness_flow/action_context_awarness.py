"""
actions/context_awarness_flow/action_context_awarness.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import time
from typing import List, Dict, Text, Any

from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import append_friendly_intro_to_answer, get_local_header
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_util_values
from actions.answer_from_file.bot_missions import get_fallback_bot_mission_with_context
from actions.answer_from_file.llm_helpers import show_prompt
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_last_conversation, log_info_text
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set_last_answer_flow, \
    get_slots_to_set_maintain_active_flow


class ActionMaintainConversationFlow(BaseDynamicLLMAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_MAINTAIN_CONV_FLOW.value

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        last_intent = tracker.get_slot("last_intent")

        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(tracker, ActionsLabel.PY_MAINTAIN_CONVERSATION_FLOW.value)
        active_flow = tracker.get_slot("active_flow")

        try:
            last_last_user_question, last_answer = get_last_conversation(tracker, action_label)

            log_info_text(action_label, "A - LOL123 - last_last_user_question : " + last_last_user_question)

            if last_second_question:
                log_info_text(action_label, "B - LOL123 - last_second_question : " + last_second_question)

            log_info_text(action_label, "B - LOL123 - last_answer : " + last_answer)

            log_info_text(action_label, "C - LOL123 - native_question : " + native_question)

            prompt = get_fallback_bot_mission_with_context(None, native_question, last_last_user_question, last_answer)
            show_prompt(action_label, prompt)

            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            # {get_local_header(elapsed, 'SECTION-ADV', PDF_PATH)} - {get_local_header(elapsed, 'EVAL-PJ', 'PATH_HIERARCY_EVALS_JURYS_MRKDN')}
            send_multiple_messages_forwarded_by_buttons(dispatcher, f"{get_local_header(elapsed, 'FALL-BACK', 'LLM')} {append_friendly_intro_to_answer(answer)}",FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_maintain_active_flow(last_second_question, native_question, answer, last_intent, None, active_flow))

        except Exception as unexpected:
            answer = await unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_last_answer_flow(active_flow, answer))

def get_forwarded_action(tracker, action_label, followup, decision_mode):

    last_intent = tracker.get_slot("last_intent")
    intent = tracker.latest_message.get("intent", {}).get("name")

    log_info_text(action_label, f"🔁 🔁 🔁 🔁 🔁 DATA : {str(last_intent)} - {intent} - {str(followup)} - {decision_mode}")

    # if last_intent in ActiveIntents.ALL_CUSTOM_INTENTS or
    if last_intent and (str(followup) == 'True' or decision_mode == 'detailed'):
        log_info_text(action_label, "🔁 🔁 🔁 🔁 🔁 PLANNING - LAST-ACTION as FALL-BACK")
        action = get_target_action(last_intent)

    else:
        log_info_text(action_label, "🔁 🔁 🔁 🔁 🔁 PLANNING - FALL-BACK")
        action = ActionsNome.ACTION_MAINTAIN_CONV_FLOW.value

    if last_intent and action:
        log_info_text(action_label, "🔁 🔁 🔁 🔁 🔁 PLANNING - FOLLOW TO intent-action : " + last_intent + " -> " + action)


    log_info_text(action_label, f"🔁 🔁 🔁 🔁 🔁 DATA FINAL : {str(last_intent)} - {str(action)}")

    return last_intent, action

def get_target_action(last_intent):
    # GROUPED Test
    if last_intent in ActiveIntents.ALL_LLM_INTENTS_PG_INFOS:
        action = ActionsNome.ACTION_PG_INFOS_PDF.value
    elif last_intent in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN or last_intent in ActiveIntents.RESULTS_INTENTS:
        action = ActionsNome.ACTION_LANG_CHAIN_ROUTING.value
    elif last_intent in ActiveIntents.ALL_EXPERTS_INTENTS:
        action = ActionsNome.ACTION_EVALUATORS_PJS.value
    elif last_intent in ActiveIntents.ALL_JSON_INTENTS:
        action = ActionsNome.ACTION_GET_RESPONSE_FROM_JSON.value
    # SINGLE Test
    elif last_intent == ActiveIntents.PRESENT_ACADEMIC_STUFF.value:
        action = ActionsNome.ACTION_ACADEMIC_STUFF.value
    else:
        action = ActionsNome.ACTION_MAINTAIN_CONV_FLOW.value

    return action