"""
actions/answer_from_file/answer_from_pdf/answer_from_pdf_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import time
from typing import List, Dict, Text, Any

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import append_friendly_intro_to_answer, get_local_header, get_extracted_slots, \
    track_prompt_decision_params
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_util_values, \
    fusion_and_call_llm, log_params, track_values
from actions.answer_from_file.answer_from_markdown.answer_from_langchain_grades_action import \
    get_native_question_domain_nbr_chunks, \
    get_comp_values_from_synonyms
from actions.answer_from_file.answer_from_pdf.pdf_rag_pdf import retrieve_context_pdf
from actions.answer_from_file.bot_missions import get_standard_bot_mission, \
    get_detailed_standard_full_last_conv_bot_mission_with_context
from actions.answer_from_file.follow_up.retrieve_decision_mode import get_decision_mode
from actions.answer_from_file.llm_helpers import rewrite_using_slots_prod_grade, get_synonyms_lookup
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS, INTENT_MAP_PG_INFO, DIRECT_HAND_LONG, DIRECT_HAND_FLAG, \
    GO_SHORT, BOT_MESSAGES
from actions.constants.EntitiesMapping import ALL_ENTITIES_MAPPINGS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text
from actions.settings.settings import settings
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set, \
    get_slots_to_set_last_answer_flow


class ActionPGInfosFromPDF(BaseDynamicLLMAction):
    def name(self) -> Text:
        return ActionsNome.ACTION_PG_INFOS_PDF.value

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        decision_infos = None
        last_sscomp_value = tracker.get_slot("sscomp")
        log_info_text("🔁 🔁 🔁 🔁 🔁  AZERTY BEGIN : ", last_sscomp_value)
        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(tracker, ActionsLabel.PY_RESPOND_FROM_PDF_FOR_PG_INFOS.value)

        try:
            slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(action_label, tracker)
            detected_slots = [slot_speciality_value, slot_grade_value, slot_sscomp_value, slot_expert_value]
            entities = ["sscomp", "speciality"]

            PDF_PATH = get_file_path(intent, INTENT_MAP_PG_INFO, settings.PATH_HIERARCHY_ALL)

            nbr_chunks = settings.RAG_DEFAULT_CHUNKS
            maintained_intent = intent
            last_intent, active_flow = skip_duplication(self, tracker, action_label)
            sscomp_entity_values = get_comp_values_from_synonyms(action_label, native_question, entities)

            native_question, domains, nbr_chunks = get_native_question_domain_nbr_chunks(last_intent,
                                                                                         native_question, intent,
                                                                                         active_flow,
                                                                                         sscomp_entity_values,
                                                                                         nbr_chunks)

            decision_mode = "short"
            if last_second_question:
                log_info_text(action_label, "INSIDE last_second_question : " + last_second_question)

                decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent)
                decision_mode = decision_infos.mode

            if decision_mode == "detailed":

                maintained_intent, last_last_user_question, last_answer = track_values(tracker, action_label, last_intent, last_second_question, intent)

                question = rewrite_using_slots_prod_grade(native_question, detected_slots,
                                                          get_synonyms_lookup(action_label, entities),
                                                          ALL_ENTITIES_MAPPINGS)

                native_question = await fusion_and_call_llm(
                    self,
                    dispatcher=dispatcher,
                    last_last_user_question=last_last_user_question,
                    question=question,
                    action_label=action_label,
                    payload_tech_error=payload_tech_error,
                    native_question_log=native_question
                )

                log_info_text(f"{DIRECT_HAND_FLAG}", f" {action_label} - SUMMARY : {native_question}")

                context = retrieve_context_pdf(native_question, pdf_path=PDF_PATH, k=4)
                prompt = get_detailed_standard_full_last_conv_bot_mission_with_context(context, native_question,
                                                                                       last_last_user_question,
                                                                                       last_answer)

            else:
                log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_SHORT}")
                log_info_text("INTENT: ", f"{intent} - {last_intent} - {domains}")

                if intent == ActiveIntents.NLU_FALLBACK.value:
                    maintained_intent = last_intent

                log_info_text(action_label, f"nbr_chunks 1 : {nbr_chunks} - {domains}")
                decision_mode = "short"
                question = rewrite_using_slots_prod_grade(native_question, detected_slots,
                                                          get_synonyms_lookup(action_label, entities),
                                                          ALL_ENTITIES_MAPPINGS)

                context = retrieve_context_pdf(question, pdf_path=PDF_PATH, k=4)

                log_params(action_label, domains, intent)

                prompt = get_standard_bot_mission(question, context)

            track_prompt_decision_params(action_label, prompt, decision_infos)
            # --------------------------
            # 4. CALL PRIMARY LLM
            # --------------------------
            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)

            send_multiple_messages_forwarded_by_buttons(dispatcher, f"{get_local_header(elapsed, 'INFO', PDF_PATH)} {append_friendly_intro_to_answer(answer)}", FEEDBACK_BUTTONS)

            log_info_text(action_label, f"🔁 🔁 🔁 🔁 🔁  AZERTY END : {last_sscomp_value}")

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set(last_sscomp_value, last_second_question, native_question, answer, maintained_intent, decision_mode))

        except Exception as unexpected:
            answer = await unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return [SlotSet("last_answer", f"UNEXPECTED_ERROR: {str(unexpected)}")]

def get_file_path(intent, intent_map, fallback_intent):
    return intent_map.get(intent, fallback_intent)

def skip_duplication(self, tracker, action_label):
    last_intent = tracker.get_slot("last_intent")
    active_flow = tracker.get_slot("active_flow")

    log_info_text(action_label, f"COMPARE : {tracker.latest_action_name} - {self.name()}")
    if tracker.latest_action_name in ActionsLabel.SKIPPED_ACTIONS_FROM_LANG_CHAIN or tracker.latest_action_name == self.name():
        log_info_text(action_label, f"{BOT_MESSAGES.get('skip_duplication')} - {action_label}")

        # Capture the slots to be set
        slots_to_set = get_return_slots_for_conversations(
            get_slots_to_set_last_answer_flow(active_flow, tracker.get_slot("last_answer"))
        )

        # Return a 3-tuple, perhaps using None for the unused variables
        # or wrapping your slots to be processed later
        return None, slots_to_set

    return last_intent, active_flow