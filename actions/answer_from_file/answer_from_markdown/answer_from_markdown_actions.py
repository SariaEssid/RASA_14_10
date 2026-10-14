"""
actions/answer_from_file/answer_from_markdown/answer_from_markdown_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import io
import re
import time
from typing import List, Dict, Text, Any

import pandas as pd
from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import append_friendly_intro_to_answer, get_local_header, normalize_text, \
    get_extracted_slots
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction, load_util_values, fusion_and_call_llm, log_params, track_values
from actions.answer_from_file.answer_from_markdown.experts_rag.action_llm_markdown import get_markdown_content
from actions.answer_from_file.answer_from_markdown.experts_rag.markdown_store import \
    retrieve_sections_with_table_dynamic_bb, \
    parse_markdown_sections, table_to_narrative_e, ROW_ANCHORS, extract_cell_value, parse_specialities_from_question
from actions.answer_from_file.bot_missions import get_standard_bot_mission, \
    get_neutral_bot_mission, get_extended_bot_mission, get_extended_bot_mission_with_alerts, \
    get_detailed_standard_full_last_conv_bot_mission_with_context, \
    get_extended_bot_mission_without_duplication, fusion_question, get_extended_bot_mission_with_alerts_with_roles, \
    give_link_label
from actions.answer_from_file.data_classes import MyConversationContextSlots
from actions.answer_from_file.llm_helpers import detect_composantes, \
    rewrite_using_slots_prod_grade, get_synonyms_lookup, get_grade_speciality_values, \
    get_sscomp_values, get_context_from_langchain_rag, get_filename_context_prompt, \
    verif_hard_qe, mapping_old_new_grades, get_util_values, track_prompt_decision_params, \
    get_decision_mode, get_clean_slot_values, skip_unrelated_action
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import FEEDBACK_BUTTONS, DIRECT_HAND_LONG, GO_DETAILS, GO_SHORT, \
    DIRECT_HAND_FLAG
from actions.constants.EntitiesMapping import COMPOSANTE_CANONICAL, EXPERTS_LABELS, ALL_ENTITIES_MAPPINGS
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text, get_last_conversation
from actions.settings.settings import settings
from actions.utils.exception_error_messages import unexpected_exception_dsi
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons
from actions.utils.slots_helpers import get_return_slots_for_conversations, get_slots_to_set_eval_pj, \
    get_slots_to_set_maintain_conv, get_slots_to_set_maintain_active_flow, get_slots_to_set_last_answer_flow


class ActionEvaluatorsAndPJ(BaseDynamicLLMAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_EVALUATORS_PJS.value

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domains_old: list[dict[str, Any]]
    ) -> List[Dict[Text, Any]]:

        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(tracker, ActionsLabel.PY_RESPOND_FROM_PDF_FOR_EVAL_PJ.value)
        last_intent = tracker.get_slot("last_intent")
        native_question = normalize_text(native_question)

        my_last_sscomp_value = tracker.get_slot("sscomp")

        try:
            maintained_intent = intent
            nbr_chunks = 2
            slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(action_label, tracker)

            entities = ["grade", "speciality", "sscomp", "expert"]
            synonyms_lookup = get_synonyms_lookup(action_label, entities)

            detected_slots = get_entity_values(native_question, synonyms_lookup, entities) # [slot_speciality_value, slot_grade_value, slot_sscomp_value, slot_expert_value]
            question = rewrite_using_slots_prod_grade(native_question, detected_slots, synonyms_lookup, ALL_ENTITIES_MAPPINGS)

            if intent == ActiveIntents.ASK_EXPERT_BY_SPEC_COMP.value:
                context = get_ask_experts_by_comp_prompt(action_label, question)
                prompt = get_neutral_bot_mission(question, context)
                tag = "BY"
                log_info_text(action_label, tag)
            elif intent == ActiveIntents.ASK_INFOS_EXPERT_BY_NAME.value:
                context = get_markdown_content(settings.PATH_HIERARCY_EVALS_JURYS_MRKDN_NAME)
                prompt = get_neutral_bot_mission(question, context)
                tag = "NAME"
                log_info_text(action_label, tag)
            elif intent == ActiveIntents.ASK_EVAL_VS_PJ.value:
                filename, context = get_context_from_langchain_rag(action_label, question, ["evalsjurys"], [], nbr_chunks)
                prompt = get_extended_bot_mission(question, context)
                tag = "VS"
                log_info_text(action_label, tag)
            else:
                context = get_markdown_content(settings.PATH_HIERARCY_EVALS_JURYS_MRKDN_ALL)
                prompt = get_standard_bot_mission(question, context)
                tag = "OTHER"
                log_info_text(action_label, tag)

            decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent)
            decision_mode = decision_infos.mode

            if decision_mode == 'detailed' and intent == ActiveIntents.NLU_FALLBACK.value:
                maintained_intent = last_intent
                last_last_user_question, last_answer = get_last_conversation(tracker, action_label)
                if tag == 'VS':
                    filename, context, prompt = get_filename_context_prompt(action_label, last_last_user_question, last_answer, native_question, maintained_intent)
                else:
                    prompt = get_detailed_standard_full_last_conv_bot_mission_with_context(context, native_question, last_last_user_question, last_answer)

            track_prompt_decision_params(action_label, prompt, decision_infos)

            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher, f"{get_local_header(elapsed, f'EVAL-PJ | {tag}', settings.PATH_HIERARCY_EVALS_JURYS_MRKDN_NAME)} {append_friendly_intro_to_answer(answer)}",FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_eval_pj(my_last_sscomp_value, slot_speciality_value, last_second_question, native_question, answer, maintained_intent, decision_mode))

        except Exception as unexpected:
            answer = unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return [SlotSet("last_answer", f"UNEXPECTED_ERROR: {str(unexpected)}")]

class ActionAcademicStuff(BaseDynamicLLMAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_ACADEMIC_STUFF.value

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domains: list[dict[str, Any]]
    ) -> List[Dict[Text, Any]]:

        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(tracker, ActionsLabel.PY_ACADEMIC_STUFF_FROM_MD.value)
        last_intent = tracker.get_slot("last_intent")
        final_native_question = native_question

        try:
            maintained_intent = intent
            nbr_chunks = 2
            get_extracted_slots(action_label, tracker)
            entities = ["grade", "speciality"]
            detected_slots = ["assistant_tech", "technologue", "maitre_tech", "professeur_tech", "efm", "efs", "efa", "ef", "elcc", "elcc1", "elcc2"]

            log_info_text("SUMMARY : ", f"{action_label} - {native_question} - {str(detected_slots)} - {str(entities)}")

            decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent)
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
                    tracker= tracker,
                    nbr_chunks=nbr_chunks,
                    action_label= action_label,
                    native_question= native_question,
                    entities= entities,
                    detected_slots= detected_slots
                )

                filename, context, question = get_filename_context(ctx)
                prompt = get_detailed_standard_full_last_conv_bot_mission_with_context(context, native_question, last_second_question, last_answer)

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

                filename, context, question = get_filename_context(ctx)
                prompt = get_extended_bot_mission(question, context)

            context += get_academic_stuff_rules()
            track_prompt_decision_params(action_label, prompt, decision_infos)

            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher, f"{get_local_header(elapsed, 'STUFF', filename)} {append_friendly_intro_to_answer(answer)}",FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, final_native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_maintain_conv(last_second_question, final_native_question, answer, maintained_intent, decision_mode))

        except Exception as unexpected:
            answer = unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, final_native_question, answer, intent, confidence)
            return [SlotSet("last_answer", f"UNEXPECTED_ERROR: {str(unexpected)}")]

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
        action_label, start_time, native_question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent = load_util_values(tracker, ActionsLabel.PY_RESPOND_FROM_LANG_CHAIN.value)

        exist_class, last_intent, active_flow = skip_unrelated_action(self, tracker, action_label, intent)

        if exist_class:
            log_info_text(action_label, "🚩 SKIP FROM CLASS : " + str(exist_class))
            return []
        log_info_text(action_label, DIRECT_HAND_FLAG + tracker.latest_action_name + " - " + self.name())

        if active_flow:
            log_info_text(action_label, "active_flow : " + str(active_flow))

        slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value = get_extracted_slots(action_label, tracker)
        detected_slots = [slot_speciality_value, slot_grade_value, slot_sscomp_value, slot_expert_value]
        entities = ["sscomp", "speciality", "grade"]

        sscomp_entity_values = get_comp_values_from_synonyms(action_label, native_question, entities)
        log_info_text(action_label, "sscomp_entity_values : " + str(sscomp_entity_values))

        if intent and last_intent :
            log_info_text(action_label, "INTENTS : " + intent + " - " + last_intent)

        try:
            nbr_chunks = 2
            maintained_intent = intent

            native_question, domains, nbr_chunks = get_native_question_domain_nbr_chunks(last_intent,
                                                                                        native_question, intent,
                                                                                        active_flow,
                                                                                        sscomp_entity_values,
                                                                                        nbr_chunks)
            log_info_text(action_label, "FLOWW - domains : " + str(domains))

            decision_mode = "short"
            is_hard = re.search(verif_hard_qe(), native_question, flags=re.IGNORECASE)

            if last_second_question:
                log_info_text(action_label, "INSIDE last_second_question : " + last_second_question)

                decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent)
                decision_mode = decision_infos.mode

            if decision_mode == "detailed":
                maintained_intent, last_last_user_question, last_answer = track_values(tracker, action_label, last_intent, last_second_question, intent)

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

                question = rewrite_using_slots_prod_grade(native_question, detected_slots, get_synonyms_lookup(action_label, entities), ALL_ENTITIES_MAPPINGS)
                filename, context, prompt = get_filename_context_prompt(action_label, last_second_question, last_answer, question, maintained_intent)

            else:
                log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_SHORT}")
                log_info_text("INTENT: ", f"{intent} - {last_intent} - {domains}")

                if intent == ActiveIntents.NLU_FALLBACK.value:
                    maintained_intent = last_intent

                if intent == ActiveIntents.HOW_AUTHENTICATE_WITH_CHATBOT or (last_intent and last_intent in ActiveIntents.RESULTS_INTENTS and intent not in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN):
                    domains = ["chatbot"]

                log_info_text(action_label, f"nbr_chunks 1 : {nbr_chunks} - {domains}")
                decision_mode = "short"
                question = rewrite_using_slots_prod_grade(native_question, detected_slots, get_synonyms_lookup(action_label, entities), ALL_ENTITIES_MAPPINGS)
                filename, context = get_context_from_langchain_rag(action_label, question, domains, [], nbr_chunks)

                log_params(action_label, domains, is_hard, intent)

                if is_hard or (intent and intent in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN_EXTEND) or (last_intent and last_intent in ActiveIntents.RESULTS_INTENTS):
                    log_info_text(action_label, "HERE .")

                    if intent == ActiveIntents.ASK_PROCEDURE_PG.value:
                        prompt = get_extended_bot_mission_with_alerts(question, context, give_link_label())
                    elif intent == ActiveIntents.ASK_ACCESS_RESOURCES_BY_EVALUATOR.value:
                        prompt = get_extended_bot_mission_with_alerts_with_roles(question, context)
                    else:
                        prompt = get_extended_bot_mission_without_duplication(question, context)
                else:
                    prompt = get_standard_bot_mission(question, context)

            # show_my_text(action_label, context)
            track_prompt_decision_params(action_label, prompt, decision_infos)
            log_info_text(action_label, "🎯 PIKO - : " + "1")
            answer = await self.call_llm_safe(
                dispatcher=dispatcher,
                prompt=prompt,
                action_label=action_label,
                payload_tech_error=payload_tech_error
            )

            elapsed = round(time.time() - start_time, 2)
            send_multiple_messages_forwarded_by_buttons(dispatcher, f"{get_local_header(elapsed, 'LANG-CHAIN', filename)} {append_friendly_intro_to_answer(answer)}",FEEDBACK_BUTTONS)

            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_maintain_active_flow(last_second_question, native_question, answer, maintained_intent, decision_mode, active_flow))

        except Exception as unexpected:
            answer = unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, str(unexpected))
            await log_chat(user_id, session_id, native_question, answer, intent, confidence)
            return get_return_slots_for_conversations(get_slots_to_set_last_answer_flow(active_flow, answer))

def get_ask_experts_by_comp_prompt(action_label, question):
    log_info_text("🔴🔴🔴🔴🔴", "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴")
    # 1. Load markdown
    markdown_raw = get_markdown_content(settings.PATH_HIERARCY_EVALS_JURYS_MRKDN_BY)
    sections = parse_markdown_sections(markdown_raw)

    retrieved_sections = retrieve_sections_with_table_dynamic_bb(sections, question, top_k=3)
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
            log_info_text("🔴 3: " , composante + "\n")

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
    else :
        context = markdown_raw
    return context

def format_values(value: str) -> str:
    return ", ".join(f"```{item.strip().upper()}```" for item in value.split(","))

def search_expert_all_roles(target_name, markdown_text):
    target_name_clean = target_name.lower().strip()
    sections = re.split(r'(##+ .*\n)', markdown_text)
    found_assignments = []

    for i in range(1, len(sections), 2):
        header = sections[i].lower()
        content = sections[i + 1]
        title = "Président de Jury" if "jury" in header else "Évaluateur"
        tables = re.findall(r'(\|.*\|(?:\n\|.*\|)*)', content)

        for table_str in tables:
            df = pd.read_csv(io.StringIO(table_str), sep="|", skipinitialspace=True).dropna(axis=1, how='all')
            df.columns = [c.strip() for c in df.columns]

            current_role = "Expert"

            for index, row in df.iterrows():
                first_col_val = str(row.iloc[0]).strip()

                if first_col_val and first_col_val not in ["nan", "-", ""]:
                    # 1. Remove Markdown stars (**)
                    clean_text = first_col_val.replace("*'", "")
                    # 2. Remove leading numbers, dots, and hyphens (e.g., "2.2 - ")
                    current_role = re.sub(r'^[\d.\s\-–—]+', '', clean_text).strip()

                elif len(row) > 1:
                    second_col_val = str(row.iloc[1]).strip()
                    if second_col_val and second_col_val not in ["nan", "-", ""]:
                        clean_text = second_col_val.replace("*'", "")
                        current_role = re.sub(r'^[\d.\s\-–—]+', '', clean_text).strip()

                for col in df.columns:
                    # Clean the column header as well
                    col_clean = col.replace("*'", "").strip()
                    cell_value = str(row[col]).lower()

                    if target_name_clean in cell_value:
                        found_assignments.append(f"```{title}``` de l'épreuve ```{current_role}``` pour la spécialité ```{col_clean}```")

    if not found_assignments:
        return None

    unique_assignments = list(dict.fromkeys(found_assignments))

    if len(unique_assignments) == 1:
        return f"{target_name} est {unique_assignments[0]}."
    else:
        assignments_str = "\n- ".join(unique_assignments)
        return f"```{target_name}``` occupe les fonctions suivantes :\n- {assignments_str}"

def get_infos_by_expert_name(action_label, tracker):

    experts_raw = list(tracker.get_latest_entity_values("expert"))
    experts = list(dict.fromkeys(experts_raw))
    log_info_text(action_label, "🎯 experts : " + str(experts))

    # Fallback if entities aren't caught but the slot is set
    if not experts:
        slot_value = tracker.get_slot("expert")
        experts = slot_value if isinstance(slot_value, list) else [slot_value]
        log_info_text(action_label, "ESSID 123 - " + str(experts))

    list_expert = []

    if experts:
        if len(experts) == 1 and experts[0] is None:
            list_expert = []
        else:
            for expert in experts:
                if expert in EXPERTS_LABELS:
                    list_expert.append(EXPERTS_LABELS[expert])

    return list_expert

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

        if "langue" in question or "Agrégé" in question:
            domains.append("elcc")
            log_info_text("👉 👉   my-domain-C : ", f"{str(domains)}")

    log_info_text("👉 👉   my-domain-D : ", f"{str(domains)}")
    return domains

def get_academic_stuff_rules():
    return """\n
- Groupe de **Spécilités Techniques** : Technologie de l'information, Électromécanique, Génie Civil, Génie énergétique, Mathématique
- Groupe de **Spécialité de Langues** : Langues et Communications

- ❌ Un candidat du **Groupe 1 (spécialités techniques)** ne peut **jamais postuler** pour un grade du **Groupe 2**.
- ❌ Un candidat du **Groupe 2 (Langues et Communication)** ne peut **jamais postuler** pour un grade du **Groupe 1**
"""

def get_native_question_domain_nbr_chunks(last_intent, native_question, intent, active_flow, sscomp_entity_values, nbr_chunks):

    domains = []

    if intent and last_intent and domains:
        log_info_text("#####PIKA intent-1 : ", last_intent + " - " + intent + " -> " + str(domains))

    if intent == ActiveIntents.NLU_FALLBACK.value:
        log_info_text(DIRECT_HAND_FLAG, "PIKA LAST-INTENT : " + last_intent)
        native_question, domains, nbr_chunks = get_util_values(last_intent, active_flow, sscomp_entity_values, native_question, domains, nbr_chunks)
    else :
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
            native_question += "" # f" **{chatbot_context}**"
            domains = ["chatbot"]
            nbr_chunks = 2
        else:
            native_question, domains, nbr_chunks = get_util_values(intent, active_flow, sscomp_entity_values, native_question, domains, nbr_chunks)

    log_info_text("##### PIKA FINAL DOMAINS : ", intent + " -> " + str(domains))

    return native_question, domains, nbr_chunks

def get_filename_context(ctx: MyConversationContextSlots):

    question, grades, specialities = get_grade_speciality_values_from_synonyms(ctx.action_label,
                                                                               ctx.native_question,
                                                                               ctx.detected_slots, ctx.entities)

    domains = detect_domain(question)
    log_info_text(ctx.action_label, f"👉   my-domain-2 : {str(domains)}")
    if not domains and not grades:
        domains = ['ef']
        grades = ['ef', 'elcc']

    grades = mapping_old_new_grades(grades)

    filename, context = get_context_from_langchain_rag(ctx.action_label, question, domains, grades, ctx.nbr_chunks)

    log_info_text(ctx.action_label, f"domains : {str(domains)}")
    log_info_text(ctx.action_label, f"NEW grades : {grades}")
    log_info_text(ctx.action_label, f"question : {question}")

    return filename, context, question

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