"""
actions/answer_from_file/llm_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import httpx
import yaml

from actions.actions import normalize_text
from actions.answer_from_file.bot_missions import get_short_standard_full_last_conv_bot_mission_with_context_alerts, \
    get_detailed_standard_full_last_conv_bot_mission_with_context, get_extended_bot_mission_with_alerts, give_format
from actions.constants.ActiveIntents import ActiveIntents
from actions.logging.logger import notify_team_leader_by_technical_problem
from actions.logging.logging_helpers import log_info_text, log_exception_text
from actions.settings.config import LANG_CHAIN_URL
from actions.settings.settings import settings


class RAGServiceUnavailable(Exception):
    pass

class HttpClientManager:

    _client: httpx.AsyncClient | None = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:

        if cls._client is None or cls._client.is_closed:

            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=5.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0)
            )

        return cls._client

    @classmethod
    async def close(cls):

        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()

        cls._client = None

##### Retrieve context from LangChain
async def get_context_from_langchain_rag(
    action_label,
    native_question,
    domains,
    grades,
    nbr_chunks
):
    try:
        client = HttpClientManager.get_client()

        response = await client.post(
            f"{LANG_CHAIN_URL}/rag/context",
            headers={
                "X-Service-Token": settings.RASA_RAG_TOKEN
            },
            json={
                "question": native_question,
                "domains": domains,
                "grades": grades,
                "nbr_chunks": nbr_chunks,
            },
        )

        if is_no_context_response(response):
            log_info_text(
                action_label,
                "RAG: no relevant context found"
            )
            return "NO_CONTEXT_FILENAME", ""

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or not isinstance(data.get("context"), str):
            raise ValueError("RAG service returned an unexpected response")

        if not data["context"].strip():
            raise ValueError("RAG service returned empty context")

        context = data.get("context") or ""
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

        await notify_team_leader_by_technical_problem(payload)

        log_exception_text(
            action_label,
            f"Failed to retrieve RAG context: {status_code} - {exc}",
        )

        raise RAGServiceUnavailable(
            "RAG context retrieval failed"
        ) from exc

def get_payload_rasa_rag_service():
    return {
        "userId": None,
        "sessionId": None,
        "userInput": None,
        "rasaIntent": str(ActiveIntents.NLU_FALLBACK.value),
        "confidence": 1,
        "messageExchangeDate": datetime.now(timezone.utc).isoformat()
    }

def is_no_context_response(response: httpx.Response) -> bool:
    """True only for the RAG service's explicit 'nothing relevant found' 404."""
    if response.status_code != 404:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    # Checking `detail` avoids hiding a real 404 (wrong URL, wrong route).
    return isinstance(body, dict) and body.get("detail") == "no_relevant_context"


##### Get Synonyms Lookup
def get_synonyms_lookup(action_label, entities):
    entity_slot_mapping = load_entity_slot_mapping("domain.yml", entities)
    synonyms_lookup = load_synonyms_grouped_by_entity(find_conf_file_path(action_label, "data", "nlu.yml"), entities, entity_slot_mapping)
    return synonyms_lookup

def load_synonyms_grouped_by_entity(nlu_file_path, requested_entities, entity_slot_mapping):
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

##################################################

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