"""
actions/answer_from_file/answer_from_json/answer_from_json_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Dict, Text, Any

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import append_friendly_intro_to_answer, get_extracted_slots, get_local_header
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_json_cached, load_util_values
from actions.answer_from_file.bot_missions import get_bot_neutral_header_mission, analyse_last_discussion, \
    get_standard_bot_mission_with_alerts, get_detailed_standard_full_last_conv_bot_mission_with_context_alerts
from actions.answer_from_file.data_classes import MyConversationContext
from actions.answer_from_file.llm_helpers import get_synonyms_lookup, rewrite_using_slots_prod_grade, \
    track_prompt_decision_params, get_decision_mode
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS, DIRECT_HAND_LONG, GO_DETAILS, GO_SHORT, DIRECT_HAND_FLAG
from actions.constants.EntitiesMapping import ALL_ENTITIES_MAPPINGS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text, get_last_conversation
from actions.settings.settings import settings
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set_json


class ActionGetResponseFromJSON(BaseDynamicLLMAction):
    def name(self) -> Text:
        return ActionsNome.ACTION_GET_RESPONSE_FROM_JSON.value

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(tracker, ActionsLabel.PY_RESPOND_FROM_JSON_FOR_STATS.value)
        last_intent = tracker.get_slot("last_intent")

        try:

            maintained_intent = intent

            slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(action_label, tracker)
            detected_slots = [slot_speciality_value, slot_session_value, slot_grade_value]
            entities = ["speciality", "session", "grade"]
            synonyms_lookup = get_synonyms_lookup(action_label, entities)
            question = rewrite_using_slots_prod_grade(native_question, detected_slots, synonyms_lookup, ALL_ENTITIES_MAPPINGS)
            slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(action_label, tracker)

            decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent)
            decision_mode = decision_infos.mode

            if decision_mode == "detailed":

                log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_DETAILS} - {intent} - {last_intent}")

                json_text, flag = get_context_flag_by_intent(last_intent)
                ctx = MyConversationContext(
                    tracker=tracker,
                    action_label=action_label,
                    last_second_question=last_second_question,
                    decision_mode=decision_mode,
                    intent=intent,
                    last_intent=last_intent,
                    question=question,
                    json_text=json_text
                )

                fallback_prompt, bot_forwarded_mission, decision_mode, maintained_intent = handle_detailed_fallback(ctx)
                prompt = fallback_prompt

            else:
                log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_SHORT} - {intent} - {last_intent}")
                json_text, flag = get_context_flag_by_intent(intent)
                prompt = get_standard_bot_mission_with_alerts(question, json_text, get_rules_instructions_stats())

            if json_text:
                log_info_text(DIRECT_HAND_FLAG, "json_text: " + json.dumps(json_text, ensure_ascii=False)[:100])


            track_prompt_decision_params(action_label, prompt, decision_infos)

            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher, f"{get_local_header(elapsed, f'JSON-{flag}', settings.RESULTS_STAT_JSON_PATH)} {append_friendly_intro_to_answer(answer)}", FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)

            if last_second_question:
                log_info_text("JSONA - 1 : ", last_second_question)

            log_info_text("JSONA - 1 : ", native_question + " - " + question)

            return get_return_slots_for_conversations(get_slots_to_set_json(slot_session_value, slot_speciality_value, slot_grade_value, last_second_question, native_question, answer, maintained_intent, decision_mode))

        except Exception as unexpected:
            answer = await unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return [SlotSet("last_answer", f"UNEXPECTED_ERROR: {str(unexpected)}")]


def get_rules_instructions_stats():
    return f"""
INSTRUCTIONS DE RÉPONSE:
1 - Si l'utilisateur donne une question sans préciser une session spécifique => réponds concernant la session {settings.ACTIVE_SESSION}
    a. Si l'état de cette session est "EN_ATTENTE" => dis que ce n'est pas disponible pour l'instant.
    b. Si l'état de cette session est "DISPONIBLE" ou "EN_COURS" => réponds."""

def handle_detailed_fallback(ctx: MyConversationContext):

    maintained_intent = ctx.last_intent

    last_last_user_question, last_answer = get_last_conversation(ctx.tracker, ctx.action_label)
    bot_forwarded_mission = f"{get_bot_neutral_header_mission()} {analyse_last_discussion()}"
    prompt = get_detailed_standard_full_last_conv_bot_mission_with_context_alerts(ctx.json_text, ctx.question, last_last_user_question, last_answer, get_rules_instructions_stats())

    return prompt, bot_forwarded_mission, "detailed", maintained_intent

def get_context_flag_by_intent(intent):
    if intent == ActiveIntents.ASK_SUCCESS_RATE.value:
        json_text = load_json_cached("results_by_sessions", Path(getattr(settings, "RESULTS_STAT_JSON_PATH")))
        flag = "STAT"
    elif intent == ActiveIntents.ASK_NBR_NEEDED_POSITIONS_BY_SPEC.value:
        json_text = load_json_cached("specialities", Path(getattr(settings, "SPECIALITIES_JSON_PATH")))
        flag = "POSITION"
    elif intent == ActiveIntents.ASK_CONCERNED_GRADES.value:
        json_text = load_json_cached("grades", Path(getattr(settings, "GRADES_JSON_PATH")))
        flag = "GRADE"
    else:
        json_text = ""
        flag = "ALL"

    log_info_text("intent : ", intent)
    log_info_text("json_text : ", json_text)
    log_info_text("flag", flag)

    return json_text, flag