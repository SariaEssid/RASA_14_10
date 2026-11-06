"""
actions/answer_from_file/common_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from actions.actions import normalize_text, get_random_message
from actions.answer_from_file.bot_missions import get_short_standard_full_last_conv_bot_mission_with_context_alerts, \
    get_detailed_standard_full_last_conv_bot_mission_with_context, get_extended_bot_mission_with_alerts, give_format
from actions.answer_from_file.llm_helpers.langchain_helpers import get_context_from_langchain_rag, \
    RAGAuthenticationError, RAGInvalidRequestError, RAGServiceUnavailable, RAGUnexpectedResponseError
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES
from actions.logging.logging_helpers import log_info_text
from actions.utils.message_helpers import send_custom_fallback_problem_to_team_leader_with_fe


##### Rewrite question using slots
def rewrite_using_slots_prod_grade(native_question, detected_slots, synonyms_lookup, canonical_mapping):

    log_info_text("ESSID123 - REWRITE - detected_slot : ", f"{detected_slots}")
    log_info_text("ESSID123 - REWRITE - BEFORE : ", f"{native_question}")

    rewritten_question = native_question.lower()

    for slot in sorted(filter(None, detected_slots), key=len, reverse=True):

        canonical_value = canonical_mapping.get(slot)
        log_info_text("ℹ️   ℹ️   ℹ️   ℹ️   ℹ️   ℹ️   ℹ️   ℹ️   slot-canonical : ", f"{slot} - {canonical_value}")
        if not canonical_value:
            continue

        entity_type = find_entity_for_slot(slot, synonyms_lookup)
        if not entity_type:
            continue

        # Clean up whitespace/newlines from synonyms list
        slot_synonyms = [s.strip() for s in synonyms_lookup.get(entity_type, {}).get(slot, [])]
        slot_terms = list(set(slot_synonyms + [str(slot).strip()]))

        log_info_text("#################### SLOTS are : ", f"{str(slot_terms)}")

        # Escape terms and wrap each term in word boundary lookarounds: (?<!\w)term(?!\w)
        escaped_terms = sorted(
            [rf"(?<!\w){re.escape(str(t))}(?!\w)" for t in slot_terms if t],
            key=len,
            reverse=True
        )

        pattern = re.compile("|".join(escaped_terms), re.IGNORECASE)

        rewritten_question = pattern.sub(canonical_value, rewritten_question)

        log_info_text("ESSID123 - REWRITED -> ", f"{pattern} * {canonical_value} => {rewritten_question}")

    log_info_text("ESSID123 - REWRITE - AFTER : ", f"{rewritten_question}")
    return rewritten_question

def find_entity_for_slot(slot, synonyms_lookup):

    for entity_name, entity_dict in synonyms_lookup.items():
        if slot in entity_dict:
            return entity_name

    return None

##### Common functions

rag_payload = {
        "userId": None,
        "sessionId": None,
        "userInput": None,
        "rasaIntent": str(ActiveIntents.NLU_FALLBACK.value),
        "confidence": 1,
        "messageExchangeDate": datetime.now(timezone.utc).isoformat()
    }
standard_user_friendly_msg = get_random_message(BOT_MESSAGES['fallback_dsi'])

async def get_filename_context_prompt(dispatcher, action_label, last_last_user_question, last_answer, full_history, maintained_intent):

    try:
        full_history = f"""{full_history.strip()}"""
        last_question = full_history.split(":")[0].strip()

        log_info_text(action_label, "👉  =====> SARSA full_history : " + full_history)
        log_info_text(action_label, "👉  =====> SARSA last_question : " + last_question)

        domains = []
        log_info_text(action_label, f"maintained_intent: {str(maintained_intent)}")

        native_question, domains, nbr_chunks = get_util_values(maintained_intent, None, None, None, domains, None)

        if domains:
            log_info_text(action_label, "============================================> domains : " + str(domains))

        filename, context = await get_context_from_langchain_rag(action_label, full_history, domains, [], 2)
        if maintained_intent == ActiveIntents.ASK_PROCEDURE_PG.value:
            log_info_text(action_label, "============================================> SARSA SHORT : " + last_question)
            prompt = get_short_standard_full_last_conv_bot_mission_with_context_alerts(context, last_question, last_last_user_question, last_answer, "")
        elif maintained_intent in ActiveIntents.RESULTS_INTENTS:
            prompt = get_extended_bot_mission_with_alerts(last_question, context, give_format())
        else:
            log_info_text(action_label, "============================================> SARSA EXTENDED : " + last_question)
            prompt = get_detailed_standard_full_last_conv_bot_mission_with_context(context, last_question, last_last_user_question, last_answer)

        return filename, context, prompt

    except RAGAuthenticationError:
        code_exception = "RAG authentication failure."
        await send_custom_fallback_problem_to_team_leader_with_fe(dispatcher, action_label, rag_payload, code_exception, standard_user_friendly_msg)
        return None, None, None

    except RAGInvalidRequestError:
        code_exception = "Invalid RAG request"
        await send_custom_fallback_problem_to_team_leader_with_fe(dispatcher, action_label, rag_payload, code_exception, standard_user_friendly_msg)
        return None, None, None

    except (RAGServiceUnavailable, RAGUnexpectedResponseError):
        code_exception = "RAG service failure"
        await send_custom_fallback_problem_to_team_leader_with_fe(dispatcher, action_label, rag_payload, code_exception, standard_user_friendly_msg)
        return None, None, None

def get_grade_speciality_values(question, synonyms_lookup):
    grade_entity_values = get_clean_slot_values(question, synonyms_lookup["grade"])
    speciality_entity_values = get_clean_slot_values(question, synonyms_lookup["speciality"])

    return grade_entity_values, speciality_entity_values

def get_clean_slot_values(question, synonyms_dict):

    detected_values = []
    remaining_text = normalize_text(question.lower())
    log_info_text("🔥 🔥   remaining_text: ", f"{remaining_text}")

    syn_pairs = []

    for canonical, examples in synonyms_dict.items():
        for ex in examples:
            syn_pairs.append((ex.lower().strip(), canonical))

    # Crucial : Trier par longueur décroissante pour attraper "Assistant Technologue" avant "Technologue"
    syn_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    for synonym, canonical in syn_pairs:
        pattern = rf"\b{re.escape(synonym)}\b"

        if re.search(pattern, remaining_text):
            log_info_text("🔥 🔥   pattern: ", f"{pattern} - {canonical}")
            detected_values.append(canonical)

            # 🔥 VERY IMPORTANT
            remaining_text = re.sub(pattern, " ", remaining_text)

    return list(set(detected_values))

def get_sscomp_values(question, synonyms_lookup):
    sscomp_entity_values = get_clean_slot_values(question, synonyms_lookup["sscomp"]) # SYNONYMS_LOOKUP["session"]
    return sscomp_entity_values

def get_util_values(intent, active_flow, sscomp_entity_values, native_question, domains, nbr_chunks):

    if intent == ActiveIntents.ASK_GRANULAR_ADVICES_PG.value:
        domains = ["granularadvices"]
        log_info_text("##### intent-1.2 : ", intent + " -> " + str(domains))
    elif intent == ActiveIntents.ASK_GLOBAL_ADVICES_PG.value:
        if active_flow == "selected_advice_plan" and len(sscomp_entity_values) == 0:
            native_question = "Proposer conseils pour réussir mon passage de grade"
        domains = ["globaladvices"]
    elif intent in ActiveIntents.ALL_DELIBERATION_INTENTS:
        domains = ["chatbot"]
    elif intent == ActiveIntents.ASK_UPDATE_PERSONAL_INFORMATION.value:
        domains = ["userprofile"]
    elif intent == ActiveIntents.ASK_ACCESS_RESOURCES_BY_EVALUATOR.value:
        domains = ["resources"]
        nbr_chunks = 1
    elif intent == ActiveIntents.ASK_LINK_VIDEO_DRIVE_IN_PDF.value:
        domains = ["deposit"]
    elif intent == ActiveIntents.ASK_MULTILINGUAL_MODE.value:
        domains = ["multilingual"]
    elif intent == ActiveIntents.ASK_ABOUT_COMP.value:
        domains = ["globalwiki"]
    elif intent == ActiveIntents.SELECT_COMP_FOR_GUIDE.value:
        domains = ["granularwiki"]
    elif intent == ActiveIntents.ASK_NORMAL_EXCEPTIONAL_METRIX.value:
        domains = ["metrix"]
    elif intent == ActiveIntents.ASK_ATTACH_PROOFS.value:
        domains = ["docs"]
    elif intent == ActiveIntents.PRESENT_PGPG_PLATEFORM.value:
        domains = ["pgpg"]
    elif intent == ActiveIntents.ASK_DEMANDE_REEVALUATION.value:
        domains = ["reevaluation"]
    elif intent == ActiveIntents.ASK_HANDLE_AUTOMATIC_EVALUATION.value:
        domains = ["automatic"]
    elif intent == ActiveIntents.ASK_PROCEDURE_PG.value:
        domains = ["procedure"]
    elif intent == ActiveIntents.ASK_ABOUT_ESB.value:
        domains = ["esb"]
    elif intent == ActiveIntents.ASK_WHO_MANAGE_SESSIONS.value:
        domains = ["session"]
    elif intent == ActiveIntents.ASK_ROLE_RH.value:
        domains = ["rh"]
    elif intent == ActiveIntents.ASK_OLD_VS_NEW_GRADES.value:
        domains = ["oldnew"]
    elif intent == ActiveIntents.GIVE_COMP_HIERARCHY.value:
        domains = ["structure"]
    elif intent == ActiveIntents.ASK_PRESENT_SARIA_ESSID.value:
        domains = ["saria"]

    return native_question, domains, nbr_chunks