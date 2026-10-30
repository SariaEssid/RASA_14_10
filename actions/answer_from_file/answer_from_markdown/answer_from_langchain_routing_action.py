"""
actions/answer_from_file/answer_from_markdown/answer_from_langchain_grades_action.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import re
import time
from typing import List, Dict, Text, Any

from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import append_friendly_intro_to_answer, get_local_header, get_extracted_slots, \
    track_prompt_decision_params
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_util_values, \
    fusion_and_call_llm, log_params, track_values
from actions.answer_from_file.bot_missions import get_standard_bot_mission, \
    get_extended_bot_mission_with_alerts, \
    get_extended_bot_mission_without_duplication, get_extended_bot_mission_with_alerts_with_roles, \
    give_link_label
from actions.answer_from_file.data_classes import RequiredValuesShortAnswers
from actions.answer_from_file.follow_up.retrieve_decision_mode import get_decision_mode
from actions.answer_from_file.llm_helpers import rewrite_using_slots_prod_grade, get_synonyms_lookup, \
    get_grade_speciality_values, \
    get_sscomp_values, get_context_from_langchain_rag, get_filename_context_prompt, get_util_values
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS, DIRECT_HAND_LONG, GO_SHORT, \
    DIRECT_HAND_FLAG, BOT_MESSAGES
from actions.constants.EntitiesMapping import ALL_ENTITIES_MAPPINGS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text
from actions.settings.settings import settings
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set_maintain_active_flow, \
    get_slots_to_set_last_answer_flow

nbr_chunks = settings.RAG_DEFAULT_CHUNKS
top_k = settings.EXPERT_TABLE_TOP_K

class ActionLangChainRouting(BaseDynamicLLMAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_LANG_CHAIN_ROUTING.value

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            my_domains: List[Dict[str, Any]]
    ) -> List[Dict[Text, Any]]:

        decision_infos = None
        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(
            tracker, ActionsLabel.PY_RESPOND_FROM_LANG_CHAIN.value)

        exist_class, last_intent, active_flow = skip_unrelated_action(self, tracker, action_label, intent)

        if exist_class:
            log_info_text(action_label, "🚩 SKIP FROM CLASS : " + str(exist_class))
            return []
        log_info_text(action_label, DIRECT_HAND_FLAG + tracker.latest_action_name + " - " + self.name())

        if active_flow:
            log_info_text(action_label, "active_flow : " + str(active_flow))

        slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(
            action_label, tracker)
        detected_slots = [slot_speciality_value, slot_grade_value, slot_sscomp_value, slot_expert_value]
        entities = ["sscomp", "speciality", "grade"]

        sscomp_entity_values = get_comp_values_from_synonyms(action_label, native_question, entities)
        log_info_text(action_label, "sscomp_entity_values : " + str(sscomp_entity_values))

        if intent and last_intent:
            log_info_text(action_label, "INTENTS : " + intent + " - " + last_intent)

        try:
            maintained_intent = intent

            native_question, domains, new_nbr_chunks = get_native_question_domain_nbr_chunks(last_intent,
                                                                                             native_question, intent,
                                                                                             active_flow,
                                                                                             sscomp_entity_values,
                                                                                             settings.RAG_DEFAULT_CHUNKS)
            log_info_text(action_label, "FLOWW - domains : " + str(domains))

            decision_mode = "short"
            is_hard = bool(re.search(verif_hard_qe(), native_question, flags=re.IGNORECASE))

            if last_second_question:
                log_info_text(action_label, "INSIDE last_second_question : " + last_second_question)

                decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question,
                                                         last_second_question, intent, last_intent)
                decision_mode = decision_infos.mode

            if decision_mode == "detailed":
                maintained_intent, last_last_user_question, last_answer = track_values(tracker, action_label,
                                                                                       last_intent,
                                                                                       last_second_question, intent)

                native_question = await fusion_and_call_llm(
                    self,
                    dispatcher=dispatcher,
                    last_last_user_question=last_last_user_question,
                    question=native_question,
                    action_label=action_label,
                    payload_tech_error=payload_tech_error,
                    native_question_log=native_question
                )

                log_info_text(f"{DIRECT_HAND_FLAG}", f" {action_label} - SUMMARY : {native_question}")

                question = rewrite_using_slots_prod_grade(native_question, detected_slots,
                                                          get_synonyms_lookup(action_label, entities),
                                                          ALL_ENTITIES_MAPPINGS)
                filename, context, prompt = await get_filename_context_prompt(action_label, last_second_question,
                                                                              last_answer, question, maintained_intent)

            else:
                if intent == ActiveIntents.NLU_FALLBACK.value:
                    maintained_intent = last_intent
                decision_mode = "short"

                ctx_answer = RequiredValuesShortAnswers(
                    action_label=action_label,
                    intent=intent,
                    last_intent=last_intent,
                    domains=domains,
                    native_question=native_question,
                    new_nbr_chunks=new_nbr_chunks,
                    detected_slots=detected_slots,
                    entities=entities,
                    is_hard=is_hard
                )

                prompt, filename = await get_short_answers(ctx_answer)

            track_prompt_decision_params(action_label, prompt, decision_infos)
            log_info_text(action_label, "🎯 PIKO - : " + "1")
            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher,
                                                        f"{get_local_header(elapsed, 'LANG-CHAIN', filename)} {append_friendly_intro_to_answer(answer)}",
                                                        FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(
                get_slots_to_set_maintain_active_flow(last_second_question, native_question, answer, maintained_intent,
                                                      decision_mode, active_flow))

        except Exception as unexpected:
            answer = await unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_last_answer_flow(active_flow, answer))

async def get_short_answers(ctx: RequiredValuesShortAnswers):
    action_label = ctx.action_label
    intent = ctx.intent
    last_intent = ctx.last_intent
    domains = ctx.domains
    native_question = ctx.native_question
    new_nbr_chunks = ctx.new_nbr_chunks
    detected_slots = ctx.detected_slots
    entities = ctx.entities
    is_hard = ctx.is_hard

    log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_SHORT}")
    log_info_text("INTENT: ", f"{intent} - {last_intent} - {domains}")

    if intent == ActiveIntents.HOW_AUTHENTICATE_WITH_CHATBOT.value or (
            last_intent and last_intent in ActiveIntents.RESULTS_INTENTS and intent not in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN):
        domains = ["chatbot"]

    log_info_text(action_label, f"nbr_chunks 1 : {new_nbr_chunks} - {domains}")

    question = rewrite_using_slots_prod_grade(native_question, detected_slots,
                                              get_synonyms_lookup(action_label, entities), ALL_ENTITIES_MAPPINGS)
    filename, context = await get_context_from_langchain_rag(action_label, question, domains, [], new_nbr_chunks)

    log_params(action_label, domains, intent)

    if is_hard or (intent and intent in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN_EXTEND) or (
            last_intent and last_intent in ActiveIntents.RESULTS_INTENTS):
        log_info_text(action_label, "HERE .")

        if intent == ActiveIntents.ASK_PROCEDURE_PG.value:
            prompt = get_extended_bot_mission_with_alerts(question, context, give_link_label())
        elif intent == ActiveIntents.ASK_ACCESS_RESOURCES_BY_EVALUATOR.value:
            prompt = get_extended_bot_mission_with_alerts_with_roles(question, context)
        else:
            prompt = get_extended_bot_mission_without_duplication(question, context)
    else:
        prompt = get_standard_bot_mission(question, context)

    return prompt, filename

def get_grade_speciality_values_from_synonyms(action_label, native_question, detected_slots, entities):
    synonyms_lookup = get_synonyms_lookup(action_label, entities)
    question = rewrite_using_slots_prod_grade(native_question, detected_slots, synonyms_lookup, ALL_ENTITIES_MAPPINGS)
    log_info_text(action_label, f"🔥  synonyms_lookup : {synonyms_lookup}")
    log_info_text(action_label, f"🔥  ALL_ENTITIES_MAPPINGS : {ALL_ENTITIES_MAPPINGS}")
    grade_entity_values, speciality_entity_values = get_grade_speciality_values(question, synonyms_lookup)
    return question, grade_entity_values, speciality_entity_values

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

def verif_hard_qe():
    keywords = [
        "de toute", "de toutes", "vs", "tous", "versus",
        "compare", "comparer", "comparez",
        "différents", "différent", "differents", "different",
        "difference", "différence",
        "explique", "expliquer", "expliquez"
    ]

    complex_qe_dict = r"\b(" + "|".join(keywords) + r")\b"
    return complex_qe_dict

def skip_unrelated_action(self, tracker, action_label, intent):
    last_intent = tracker.get_slot("last_intent") or None
    active_flow = tracker.get_slot("active_flow") or None
    exist_class = None

    if last_intent:
        log_info_text(action_label, DIRECT_HAND_FLAG + last_intent)
    log_info_text(action_label, DIRECT_HAND_FLAG + intent)

    if tracker.latest_action_name == self.name() or (intent == last_intent and intent not in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN) or (intent == ActiveIntents.NLU_FALLBACK.value and last_intent not in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN and last_intent not in ActiveIntents.RESULTS_INTENTS):  # or (intent not in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN)
        log_info_text(action_label, f"{BOT_MESSAGES.get('skip_unrelated_action')} - {action_label}")
        exist_class = True
        return exist_class, last_intent, active_flow

    return exist_class, last_intent, active_flow
