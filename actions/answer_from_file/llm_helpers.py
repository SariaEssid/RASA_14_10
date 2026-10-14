"""
actions/answer_from_file/llm_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations
import httpx

import os
from datetime import datetime, timezone
from typing import List, cast

import yaml

from actions.actions import normalize_text, check_is_excluded, remove_excluded_patterns, START_WORDS
from actions.answer_from_file.bot_missions import get_short_standard_full_last_conv_bot_mission_with_context_alerts, \
    get_detailed_standard_full_last_conv_bot_mission_with_context, get_extended_bot_mission_with_alerts, give_format, \
    check_is_dead_end_prompt
from actions.answer_from_file.follow_up.detect_rooting import FollowUpDetector
from actions.answer_from_file.follow_up.pron_det_checking import check_pronoun_det
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES, DIRECT_HAND_FLAG
from actions.logging.logger import notify_team_leader_by_technical_problem
from actions.logging.logging_helpers import log_info_text, log_exception_text
from actions.semantic.semantic_actions import is_followup
from actions.settings.config import LANG_CHAIN_URL
from actions.settings.settings import settings
from actions.utils.slots_helpers import get_slots_to_set_last_answer_flow, get_return_slots_for_conversations

class RAGServiceUnavailable(Exception):
    pass

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

BLOCKAGE_PATTERNS = [
    r"\baucun\b",
    r"\baucune\b",
    r"\brien\b",
    r"\n'\b",
    r"\n'\b",
    r"\bne\b",
    r"\bpas\b",
    r"\bnon\b"
]

def check_more_details(current_question: str) -> bool:
    # Matches 'detail', 'détail', 'details', 'détails', 'detailler', 'détailler', 'detaille', etc.
    pattern = r"\bd[eé]tail"
    return bool(re.search(pattern, current_question, re.IGNORECASE))

def check_is_blocked_pattern(current_question: str) -> bool:
    return any(re.search(pattern, current_question, re.IGNORECASE) for pattern in BLOCKAGE_PATTERNS)

def is_started_with_keyword(question: str) -> bool:
    if not question:
        return False

    cleaned_question = question.strip().lower()

    return cleaned_question.startswith(START_WORDS)

def detect_composantes(question: str) -> List[str]:
    """
    Detects ONE or MANY composantes from a user question.
    Returns canonical composante names used in ROW_ANCHORS.
    """

    q = normalize_text(question)

    # 🔒 Canonical composantes (MUST match ROW_ANCHORS keys)
    COMPOSANTE_KEYWORDS = {
        "production rdi": ["production rdi", "prod rdi", "rdi"],
        "dossier": ["dossier", "pj", "pièces jointes", "pieces jointes"],
        "entretien avec le jury": ["entretien", "jury", "entretien avec le jury"],
        "sequence d'enseignement": ["séquence", "sequence d'enseignement", "sequence d enseignement", "sequence enseignement"],
        "supports pedagogiques": ["supports", "support"],
        "capsules pedagogiques": ["capsules", "capsule"],
        "dissertations": ["dissertations", "dissertation"]
    }

    detected = []

    for composante, keywords in COMPOSANTE_KEYWORDS.items():
        for kw in keywords:
            # strict word boundary to avoid noise
            if re.search(rf"\b{re.escape(kw)}\b", q):
                detected.append(composante)
                break

    # preserve order of appearance in question
    detected_sorted = sorted(
        detected,
        key=lambda c: q.find(
            next(
                key_word for key_word in COMPOSANTE_KEYWORDS[c] if key_word in q
            )
        )
    )

    return detected_sorted

def get_file_path(intent, intent_map, fallback_intent):
    return intent_map.get(intent, fallback_intent)

def show_prompt(action_label, prompt):
    log_info_text("", "\n1 🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺")
    log_info_text(action_label, prompt)
    log_info_text("", "2🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺🔺\n")

def load_synonyms_grouped_by_entity(
    nlu_file_path,
    requested_entities,
    entity_slot_mapping
):
    """
    entity_slot_mapping example:
    {
        "speciality": ["math", "tic", "elct_mkn"],
        "session": ["session_25-26", "session_24-25"],
        "grade": ["lcom", "maitre_assistant"]
    }
    """

    grouped_synonyms = {entity: {} for entity in requested_entities}

    with open(nlu_file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for item in data.get("nlu", []):

        if "synonym" not in item:
            continue

        slot_name = item["synonym"]

        # 👇 Detect entity of this slot
        entity_name = None
        for entity, slots in entity_slot_mapping.items():
            if slot_name in slots:
                entity_name = entity
                break

        if entity_name not in requested_entities:
            continue

        examples_block = item.get("examples", "")

        synonyms = [
            line.strip("- ").strip()
            for line in examples_block.split("\n")
            if line.strip()
        ]

        grouped_synonyms[entity_name][slot_name] = synonyms

    return grouped_synonyms

def find_conf_file_path(action_label, folder_label, file_name):
    # 1. On part de l'emplacement du fichier actuel (llm_helpers.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. On remonte de deux niveaux pour arriver à la racine 'chatbot_RASA'
    # actions/answer_from_file -> actions -> chatbot_RASA
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # 3. On construit le chemin vers le dossier data
    if folder_label is None:
        file_path = os.path.join(project_root, file_name)
    else:
        file_path = os.path.join(project_root, folder_label, file_name)

    if not os.path.exists(file_path):
        # Optionnel : chercher directement à la racine au cas où
        nlu_path_root = os.path.join(project_root, file_name)
        if os.path.exists(nlu_path_root):
            return nlu_path_root

        raise FileNotFoundError(f"{file_name} introuvable. Chemin testé : {file_path}")

    log_info_text(action_label, "ESSID path" + file_path)
    return file_path

import re

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

def rewrite_using_slots_prod_grade_0109(native_question, detected_slots, synonyms_lookup, canonical_mapping):

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

        slot_synonyms = synonyms_lookup.get(entity_type, {}).get(slot, [])
        slot_terms = list(set(slot_synonyms + [slot]))

        log_info_text("#################### SLOTS are : ", f"{str(slot_terms)}")

        escaped_terms = sorted(
            [re.escape(str(t)) for t in slot_terms],
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

def load_entity_slot_mapping(domain_path: str, required_slots: list):
    with open(domain_path, "r", encoding="utf-8") as f:
        domain = yaml.safe_load(f)

    slots = domain.get("slots", {})

    entity_slot_mapping = {}

    for slot_name, slot_data in slots.items():
        if slot_name in required_slots:
            if slot_data.get("type") == "categorical":
                entity_slot_mapping[slot_name] = slot_data.get("values", [])

    # log_info_text(action_label, "ESSID - ENTITIES" + str(entity_slot_mapping))
    return entity_slot_mapping

def get_synonyms_lookup(action_label, entities):
    entity_slot_mapping = load_entity_slot_mapping("domain.yml", entities)
    synonyms_lookup = load_synonyms_grouped_by_entity(find_conf_file_path(action_label, "data", "nlu.yml"), entities, entity_slot_mapping)
    return synonyms_lookup

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

def get_grade_speciality_values(question, synonyms_lookup):
    grade_entity_values = get_clean_slot_values(question, synonyms_lookup["grade"])
    speciality_entity_values = get_clean_slot_values(question, synonyms_lookup["speciality"])

    return grade_entity_values, speciality_entity_values

def get_sscomp_values(question, synonyms_lookup):
    sscomp_entity_values = get_clean_slot_values(question, synonyms_lookup["sscomp"]) # SYNONYMS_LOOKUP["session"]
    return sscomp_entity_values

async def get_context_from_langchain_rag(
    action_label, native_question, domains, grades, nbr_chunks
):
    try:
        timeout = httpx.Timeout(60.0, connect=5.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{LANG_CHAIN_URL}/rag/context",
                headers={"X-Service-Token": settings.RASA_RAG_TOKEN},
                json={
                    "question": native_question,
                    "domains": domains,
                    "grades": grades,
                    "nbr_chunks": nbr_chunks,
                },
            )
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, dict) or not isinstance(data.get("answer"), str):
            raise ValueError("RAG service returned an unexpected response")

        if not data["answer"].strip():
            raise ValueError("RAG service returned empty context")

        context = data.get("answer") or ""
        filename = data.get("source_file") or "unknown"

        log_info_text(action_label, f"domains: {domains}")
        log_info_text(action_label, f"grades: {grades}")
        log_info_text(action_label, f"filename: {filename}")
        log_info_text(action_label, f"nbr_chunks: {nbr_chunks}")

        return filename, context

    except (httpx.HTTPError, ValueError) as exc:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)

        payload = get_payload_rasa_rag_service()
        payload["botReply"] = "RAG context retrieval failed"
        notify_team_leader_by_technical_problem(payload)
        log_exception_text(
            action_label,
            f"Failed to retrieve RAG context: {status_code} - {exc}",
        )

        raise RAGServiceUnavailable("RAG context retrieval failed") from exc

async def get_filename_context_prompt(action_label, last_last_user_question, last_answer, full_history, maintained_intent):
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

def exist_pronoun(last_second_question, question):
    muted_words = ["greet", "bye"]

    log_info_text("PLAN-1 : ", str(normalize_text(question)) + " - " + str(len(question.split())))

    is_excluded = None
    if check_is_excluded(question):
        is_excluded = True
        # is_pron_in_qe = False   1. donner la mission pour efm | 2. est ce que cet enseignant peut postuler pour un autre grade

    no_muted_words_found = last_second_question is not None and all(
        word.lower() not in last_second_question.lower()
        for word in muted_words
    )

    qe_without_excluded = remove_excluded_patterns(question)
    log_info_text("PLAN-3 : ", qe_without_excluded)
    is_started_with_kw = is_started_with_keyword(normalize_text(qe_without_excluded))

    log_info_text("PLAN-1 is_pron_in_qe : ", str(is_started_with_kw))

    return is_excluded, is_started_with_kw, no_muted_words_found

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

def get_util_values(intent, active_flow, sscomp_entity_values, native_question, domains, nbr_chunks):

    if intent in ActiveIntents.MANAGE_PWDS_INTENTS:
        domains = ["mdp"]
        log_info_text("##### intent-1.1 : ", intent + " -> " + str(domains))
    elif intent == ActiveIntents.ASK_GRANULAR_ADVICES_PG.value:
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


def track_prompt_decision_params(action_label, prompt, decision_infos):
    log_info_text(action_label, "🎯 prompting : " + prompt)
    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label}: \n")
    if decision_infos:
        log_info_text("👉  ROUTING SCORE: ", f"{decision_infos.score} => {decision_infos.mode}")
        for key, value in decision_infos.reasons.items():
            log_info_text(f"-  {key} ", f"{value}")

    log_info_text(action_label, "\n")

def compute_similarity(current_q: str, last_q: str) -> float:
    # Guard clause: if inputs are missing, return 0.0 immediately
    if not current_q or not last_q:
        return 0.0

    try:
        return is_followup(current_q, last_q)
    except (ValueError, TypeError, AttributeError) as e:
        # Catch specific errors related to string processing or math
        log_info_text("EXCEPTION : ", str(e))
        return 0.0

async def get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent) :

    last_user_response = tracker.get_slot("last_answer")
    detector = FollowUpDetector()
    signals = signal_extract(native_question, last_second_question)
    similarity = compute_similarity(native_question, last_second_question)

    is_pron_det = check_pronoun_det(native_question)

    is_dead_end = None
    is_blocked_pattern = check_is_blocked_pattern(native_question)
    if is_blocked_pattern:
        log_info_text("last_user_response : ",last_user_response)
        log_info_text("B L O C K E D   P A T T E R N : ", str(is_blocked_pattern))
        is_dead_end = await check_is_dead_end(self, dispatcher, action_label, last_second_question, last_user_response, native_question)
        log_info_text("RESULT : ", str(is_dead_end))

    is_more_det = check_more_details(native_question)

    log_info_text("is_pron_detis_pron_det : ", str(is_pron_det))
    decision = detector.compute_score(
        similarity=similarity,
        is_started_with_kw=signals["is_started_with_kw"],
        intent=intent,
        last_intent=last_intent,
        pron_det=is_pron_det,
        is_dead_end=is_dead_end,
        is_more_det = is_more_det,
        muted_intents=cast(List[str], ActiveIntents.MUTED_INTENTS)
    )

    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label} - ROUTING SCORE: {decision.score}")
    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label} - ROUTING MODE: {decision.mode}")
    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label} - ROUTING REASONS: {decision.reasons}")

    return decision

def signal_extract(question: str, last_question: str):

    is_excluded, is_started_with_kw, no_muted = exist_pronoun(last_question, question)

    return {
        "is_started_with_kw": bool(is_started_with_kw),
        "is_excluded": bool(is_excluded),
        "no_muted": no_muted
    }

async def check_is_dead_end(self, dispatcher, action_label, last_question, last_response, current_question):

    prompt = check_is_dead_end_prompt(last_question, last_response, current_question)

    log_info_text("DEAD END - 1 : ", prompt)
    answer = await self.call_llm_safe(
        dispatcher=dispatcher,
        prompt=prompt,
        action_label=action_label,
        payload_tech_error=None
    )
    log_info_text("🎯 DEAD END - 2 : ", answer)

    return answer

def get_payload_rasa_rag_service():
    return {
        "userId": None,
        "sessionId": None,
        "userInput": None,
        "rasaIntent": str(ActiveIntents.NLU_FALLBACK.value),
        "confidence": 1,
        "messageExchangeDate": datetime.now(timezone.utc).isoformat()
    }