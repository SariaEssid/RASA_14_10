"""
actions/answer_from_file/answer_from_markdown/answer_from_langchain_grades_action.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import re
import time
from typing import List, Dict, Text, Any

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import append_friendly_intro_to_answer, get_local_header, normalize_text, \
    get_extracted_slots, track_prompt_decision_params
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_util_values
from actions.answer_from_file.answer_from_markdown.experts_rag.action_llm_markdown import get_markdown_content
from actions.answer_from_file.answer_from_markdown.experts_rag.markdown_store import \
    parse_markdown_sections, table_to_narrative_e, ROW_ANCHORS, extract_cell_value, parse_specialities_from_question, \
    retrieve_sections_with_table_dynamic_bb
from actions.answer_from_file.bot_missions import get_standard_bot_mission, \
    get_neutral_bot_mission, get_extended_bot_mission, get_detailed_standard_full_last_conv_bot_mission_with_context
from actions.answer_from_file.follow_up.retrieve_decision_mode import get_decision_mode
from actions.answer_from_file.llm_helpers import rewrite_using_slots_prod_grade, get_synonyms_lookup, get_context_from_langchain_rag, get_filename_context_prompt, get_clean_slot_values
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS
from actions.constants.EntitiesMapping import COMPOSANTE_CANONICAL, ALL_ENTITIES_MAPPINGS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text, get_last_conversation
from actions.settings.settings import settings
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set_eval_pj

nbr_chunks = settings.RAG_DEFAULT_CHUNKS
top_k = settings.EXPERT_TABLE_TOP_K


class ActionEvaluatorsAndPJ(BaseDynamicLLMAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_EVALUATORS_PJS.value

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domains_old: list[dict[str, Any]]
    ) -> List[Dict[Text, Any]]:

        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(
            tracker, ActionsLabel.PY_RESPOND_FROM_PDF_FOR_EVAL_PJ.value)
        last_intent = tracker.get_slot("last_intent")
        native_question = normalize_text(native_question)

        my_last_sscomp_value = tracker.get_slot("sscomp")

        try:
            maintained_intent = intent
            slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(
                action_label, tracker)

            entities = ["grade", "speciality", "sscomp", "expert"]
            synonyms_lookup = get_synonyms_lookup(action_label, entities)

            detected_slots = get_entity_values(native_question, synonyms_lookup,
                                               entities)  # [slot_speciality_value, slot_grade_value, slot_sscomp_value, slot_expert_value]
            question = rewrite_using_slots_prod_grade(native_question, detected_slots, synonyms_lookup,
                                                      ALL_ENTITIES_MAPPINGS)

            if intent == ActiveIntents.ASK_EXPERT_BY_SPEC_COMP.value:
                context = get_ask_experts_by_comp_prompt(action_label, question)
                prompt = get_neutral_bot_mission(question, context)
                tag = "BY"
                log_info_text(action_label, tag)
            elif intent == ActiveIntents.ASK_INFOS_EXPERT_BY_NAME.value:
                context = get_markdown_content(settings.PATH_HIERARCHY_EVALS_JURYS_MRKDN_NAME)
                prompt = get_neutral_bot_mission(question, context)
                tag = "NAME"
                log_info_text(action_label, tag)
            elif intent == ActiveIntents.ASK_EVAL_VS_PJ.value:
                filename, context = await get_context_from_langchain_rag(action_label, question, ["evalsjurys"], [],
                                                                         nbr_chunks)

                prompt = get_extended_bot_mission(question, context)
                tag = "VS"
                log_info_text(action_label, tag)
            else:
                context = get_markdown_content(settings.PATH_HIERARCHY_EVALS_JURYS_MRKDN_ALL)
                prompt = get_standard_bot_mission(question, context)
                tag = "OTHER"
                log_info_text(action_label, tag)

            decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question,
                                                     last_second_question, intent, last_intent)
            decision_mode = decision_infos.mode

            if decision_mode == 'detailed' and intent == ActiveIntents.NLU_FALLBACK.value:
                maintained_intent = last_intent
                last_last_user_question, last_answer = get_last_conversation(tracker, action_label)
                if tag == 'VS':
                    filename, context, prompt = await get_filename_context_prompt(action_label, last_last_user_question,
                                                                                  last_answer, native_question,
                                                                                  maintained_intent)
                else:
                    prompt = get_detailed_standard_full_last_conv_bot_mission_with_context(context, native_question,
                                                                                           last_last_user_question,
                                                                                           last_answer)

            track_prompt_decision_params(action_label, prompt, decision_infos)

            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher,
                                                        f"{get_local_header(elapsed, f'EVAL-PJ | {tag}', settings.PATH_HIERARCHY_EVALS_JURYS_MRKDN_NAME)} {append_friendly_intro_to_answer(answer)}",
                                                        FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(
                get_slots_to_set_eval_pj(my_last_sscomp_value, slot_speciality_value, last_second_question,
                                         native_question, answer, maintained_intent, decision_mode))

        except Exception as unexpected:
            answer = await unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return [SlotSet("last_answer", f"UNEXPECTED_ERROR: {str(unexpected)}")]

def get_ask_experts_by_comp_prompt(action_label, question):
    log_info_text("🔴🔴🔴🔴🔴", "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴")
    # 1. Load markdown
    markdown_raw = get_markdown_content(settings.PATH_HIERARCHY_EVALS_JURYS_MRKDN_BY)
    sections = parse_markdown_sections(markdown_raw)

    retrieved_sections = retrieve_sections_with_table_dynamic_bb(sections, question, top_k=top_k)
    # 2️⃣ Detect composantes & specialities
    raw_composantes = detect_composantes(question)  # e.g., ['production rdi', 'dossier']

    log_info_text(action_label, "🎯 raw_composantes" + str(raw_composantes))
    target_composantes = [
        COMPOSANTE_CANONICAL[c]
        for c in raw_composantes
        if c in COMPOSANTE_CANONICAL
    ]
    target_sps = parse_specialities_from_question(question)  # e.g., ['Électromécanique', 'Mathématiques']

    log_info_text(action_label, "🎯 COMPOSANTES" + str(target_composantes))
    log_info_text(action_label, "🎯 SPECIALITES" + str(target_sps))

    log_info_text(action_label, "ESSID-2 retrieved_sections : " + str(retrieved_sections))
    final_values = {}  # {specialite: evaluateurs}

    for composante in target_composantes:
        final_values[composante] = {}
        section_anchors = ROW_ANCHORS.get(composante, [])
        for s in retrieved_sections:
            full_narrative = table_to_narrative_e(s["content"])

            log_info_text(action_label, str(target_sps))
            log_info_text(action_label, str(section_anchors))
            log_info_text("🔴 3: ", composante + "\n")

            for line in full_narrative.splitlines():
                if "LIGNE_OFFICIELLE" not in line:
                    continue

                # STRICT ANCHOR CHECK
                # Ensures that "2.2" is the actual ID of the component, not just "somewhere" in the line
                if not any(re.search(rf":\s*\b{re.escape(a.lower())}\b", line.lower()) for a in section_anchors):
                    continue

                # LOG THIS SPECIFIC LINE
                log_info_text(action_label, "🎯 MATCHED CORRECT LINE: " + line)

                for sp in target_sps:
                    val = extract_cell_value(line, sp, composante)
                    final_values[composante][sp] = (
                        val if val not in {"-", ".", ""} else "NON_SPECIFIE"
                    )

    log_info_text(action_label, str(final_values))

    formatted_blocks = []
    for composante, sp_map in final_values.items():
        parts = [
            f"{format_values(v)} est/sont (évaluateur(s)) pour ```{sp}```" if v != "NON_SPECIFIE" else f"Aucun évaluateur spécifié pour {sp}"
            for sp, v in sp_map.items()
        ]
        formatted_blocks.append("; ".join(parts) + f"concernant {composante}")

    evaluators_text = "\n".join(formatted_blocks)
    specialites_text = ", ".join(target_sps)
    composantes_text = ", ".join(target_composantes)

    log_info_text(action_label, "✅ EXTRACTED final_values: " + str(final_values))
    log_info_text(action_label, "✅ EXTRACTED specialites_text: " + specialites_text)
    log_info_text(action_label, "✅ EXTRACTED evaluators_text: " + evaluators_text)
    log_info_text(action_label, "✅ EXTRACTED composantes_text: " + composantes_text)

    if composantes_text and specialites_text:
        context = f"""
## Composantes : {composantes_text}
## Spécialités : {specialites_text}

## Données :
{evaluators_text}"""
    else:
        context = markdown_raw
    return context

def get_entity_values(question, synonyms_lookup, entity_types):
    """
    Dynamically extracts slot values for a list of entity types.

    :param question: The input text to analyze.
    :param synonyms_lookup: Dictionary containing synonym mappings.
    :param entity_types: List of strings representing the keys to extract (e.g., ['session', 'speciality']).
    :return: A dictionary where keys are entity types and values are the extracted slots.
    """

    all_detected_slots = []

    for entity in entity_types:
        # Extract values using the provided lookup for the specific entity type
        values = get_clean_slot_values(question, synonyms_lookup.get(entity, {}))

        # 🔥 FIX: Use .extend() instead of .append() to flatten the list
        all_detected_slots.extend(values)

        # Dynamic logging
        log_info_text("{entity}_current_values : ", f"{len(values)} - {values}")

    log_info_text("current_values : ", f"{all_detected_slots}")
    return all_detected_slots

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

def format_values(value: str) -> str:
    return ", ".join(f"```{item.strip().upper()}```" for item in value.split(","))