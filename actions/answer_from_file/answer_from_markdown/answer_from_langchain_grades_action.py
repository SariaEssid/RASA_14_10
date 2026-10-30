"""
actions/answer_from_file/answer_from_markdown/answer_from_langchain_grades_action.py

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
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_util_values
from actions.answer_from_file.bot_missions import get_extended_bot_mission, \
    get_detailed_standard_full_last_conv_bot_mission_with_context, \
    fusion_question
from actions.answer_from_file.data_classes import MyConversationContextSlots
from actions.answer_from_file.follow_up.retrieve_decision_mode import get_decision_mode
from actions.answer_from_file.llm_helpers import rewrite_using_slots_prod_grade, get_synonyms_lookup, \
    get_grade_speciality_values, \
    get_sscomp_values, get_context_from_langchain_rag, get_util_values
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS, DIRECT_HAND_LONG, GO_DETAILS, GO_SHORT, \
    DIRECT_HAND_FLAG
from actions.constants.EntitiesMapping import ALL_ENTITIES_MAPPINGS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text, get_last_conversation
from actions.settings.settings import settings
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set_maintain_conv

nbr_chunks = settings.RAG_DEFAULT_CHUNKS
top_k = settings.EXPERT_TABLE_TOP_K

class ActionAcademicStuff(BaseDynamicLLMAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_ACADEMIC_STUFF.value

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domains: list[dict[str, Any]]
    ) -> List[Dict[Text, Any]]:

        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(
            tracker, ActionsLabel.PY_ACADEMIC_STUFF_FROM_MD.value)
        last_intent = tracker.get_slot("last_intent")
        final_native_question = native_question

        try:
            maintained_intent = intent
            get_extracted_slots(action_label, tracker)
            entities = ["grade", "speciality"]
            detected_slots = ["assistant_tech", "technologue", "maitre_tech", "professeur_tech", "efm", "efs", "efa",
                              "ef", "elcc", "elcc1", "elcc2"]

            log_info_text("SUMMARY : ", f"{action_label} - {native_question} - {str(detected_slots)} - {str(entities)}")

            decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question,
                                                     last_second_question, intent, last_intent)
            decision_mode = decision_infos.mode
            if decision_mode == "detailed":
                log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_DETAILS}")
                maintained_intent = last_intent
                last_last_user_question, last_answer = get_last_conversation(tracker, action_label)

                prompt_qe = fusion_question(last_last_user_question, native_question)
                log_info_text(action_label + "FUSIONNED QUESTIONS : ", prompt_qe)
                native_question = await self.call_llm_safe(
                    dispatcher=dispatcher,
                    prompt=prompt_qe,
                    action_label=action_label,
                    payload_tech_error=payload_tech_error
                )

                final_native_question = native_question

                ctx = MyConversationContextSlots(
                    tracker=tracker,
                    nbr_chunks=nbr_chunks,
                    action_label=action_label,
                    native_question=native_question,
                    entities=entities,
                    detected_slots=detected_slots
                )

                filename, context, question = await get_filename_context(ctx)
                prompt = get_detailed_standard_full_last_conv_bot_mission_with_context(context, native_question,
                                                                                       last_second_question,
                                                                                       last_answer)

            else:
                log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_SHORT}")

                ctx = MyConversationContextSlots(
                    tracker=tracker,
                    nbr_chunks=nbr_chunks,
                    action_label=action_label,
                    native_question=native_question,
                    entities=entities,
                    detected_slots=detected_slots
                )

                filename, context, question = await get_filename_context(ctx)
                prompt = get_extended_bot_mission(question, context)

            track_prompt_decision_params(action_label, prompt, decision_infos)

            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher,
                                                        f"{get_local_header(elapsed, 'STUFF', filename)} {append_friendly_intro_to_answer(answer)}",
                                                        FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, final_native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(
                get_slots_to_set_maintain_conv(last_second_question, final_native_question, answer, maintained_intent,
                                               decision_mode))

        except Exception as unexpected:
            answer = await unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, final_native_question, answer, intent, confidence)
            return [SlotSet("last_answer", f"UNEXPECTED_ERROR: {str(unexpected)}")]

async def get_filename_context(ctx: MyConversationContextSlots):
    question, grades, specialities = get_grade_speciality_values_from_synonyms(ctx.action_label,
                                                                               ctx.native_question,
                                                                               ctx.detected_slots, ctx.entities)

    domains = detect_domain(question)
    log_info_text(ctx.action_label, f"👉   my-domain-2 : {str(domains)}")
    if not domains and not grades:
        domains = ['ef']
        grades = ['ef', 'elcc']

    grades = mapping_old_new_grades(grades)

    filename, context = await get_context_from_langchain_rag(ctx.action_label, question, domains, grades,
                                                             ctx.nbr_chunks)

    log_info_text(ctx.action_label, f"domains : {str(domains)}")
    log_info_text(ctx.action_label, f"NEW grades : {grades}")
    log_info_text(ctx.action_label, f"question : {question}")

    return filename, context, question

def get_grade_speciality_values_from_synonyms(action_label, native_question, detected_slots, entities):
    synonyms_lookup = get_synonyms_lookup(action_label, entities)
    question = rewrite_using_slots_prod_grade(native_question, detected_slots, synonyms_lookup, ALL_ENTITIES_MAPPINGS)
    log_info_text(action_label, f"🔥  synonyms_lookup : {synonyms_lookup}")
    log_info_text(action_label, f"🔥  ALL_ENTITIES_MAPPINGS : {ALL_ENTITIES_MAPPINGS}")
    grade_entity_values, speciality_entity_values = get_grade_speciality_values(question, synonyms_lookup)
    return question, grade_entity_values, speciality_entity_values

def get_native_question_domain_nbr_chunks(last_intent, native_question, intent, active_flow, sscomp_entity_values, old_nbr_chunks):
    domains = []

    if intent == ActiveIntents.NLU_FALLBACK.value:
        if last_intent:
            log_info_text(DIRECT_HAND_FLAG, "PIKA LAST-INTENT : " + last_intent)
            native_question, domains, old_nbr_chunks = get_util_values(
                last_intent, active_flow, sscomp_entity_values,
                native_question, domains, old_nbr_chunks
            )
        else:
            log_info_text(DIRECT_HAND_FLAG, "PIKA LAST-INTENT is unavailable")
    else:
        log_info_text(DIRECT_HAND_FLAG, "PIKA INTENT : " + intent)
        if (
                last_intent and
                (
                        (intent == ActiveIntents.HOW_AUTHENTICATE_WITH_CHATBOT.value and (
                                last_intent in ActiveIntents.RESULTS_INTENTS or last_intent == ActiveIntents.HOW_AUTHENTICATE_WITH_CHATBOT.value))
                        or
                        (intent == ActiveIntents.NLU_FALLBACK.value and (
                                last_intent in ActiveIntents.RESULTS_INTENTS or last_intent == ActiveIntents.HOW_AUTHENTICATE_WITH_CHATBOT.value))
                )
        ):
            native_question += ""  # f" **{chatbot_context}**"
            domains = ["chatbot"]
            old_nbr_chunks = 2
        else:
            native_question, domains, old_nbr_chunks = get_util_values(intent, active_flow, sscomp_entity_values,
                                                                       native_question, domains, old_nbr_chunks)

    log_info_text("##### PIKA FINAL DOMAINS : ", str(intent) + " -> " + str(domains))

    return native_question, domains, old_nbr_chunks

def get_comp_values_from_synonyms(action_label, native_question, entities):
    synonyms_lookup = get_synonyms_lookup(action_label, entities)
    sscomp_entity_values = get_sscomp_values(native_question, synonyms_lookup)
    return sscomp_entity_values

def detect_domain(question: str):
    question = question.lower()
    domains = []
    log_info_text("👉 👉   my-domain-A : ", f"{question} - {str(domains)}")
    if "procedure " not in question and "procédure" not in question:
        if "formateur" in question or "technologue" in question:
            domains.append("ef")
            log_info_text("👉 👉   my-domain-B : ", f"{str(domains)}")

        if "langue" in question or "agrégé" in question:
            domains.append("elcc")
            log_info_text("👉 👉   my-domain-C : ", f"{str(domains)}")

    log_info_text("👉 👉   my-domain-D : ", f"{str(domains)}")
    return domains

def mapping_old_new_grades(original_grades):

    MAPPING_OLD_NEW_GRADES = {
        'tech': 'ef',
        'maitre_tech': 'efs',
        'assistant_tech': 'efa',
        'professeur_tech': 'efm'
    }

    # Use a list comprehension to transform the list
    # .get(item, item) ensures that if a value isn't in the mapping, it stays as is

    log_info_text("OLD grades : ", original_grades)
    grades = original_grades
    if original_grades:
        grades = [MAPPING_OLD_NEW_GRADES.get(slot, slot) for slot in original_grades]

    return grades