"""
actions/grade_passage_results/dynamic_faq_result.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import json
import logging
from typing import Text, Dict, Any, List
from typing import TypeVar

from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import get_payload, get__decision_mode__last_intent
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES
from actions.constants.FlowType import FlowType, SSCOMP_TO_FLOW
from actions.grade_passage_results.data_classes import ActionContext, DynamicToChainContext
from actions.grade_passage_results.helpers import get_auth_binding_json, process_final_results_response, \
    get_bilan_final_results
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_with_log, log_info_text, log_exception_text
from actions.semantic.semantic_actions import flatten_events
from actions.settings.settings import settings
from actions.utils.error_handling import handle_action_errors
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import send_message_forwarded_by_buttons
from actions.utils.slots_helpers import get_conversational_slots, get_return_slots_qa_intent_flow_results, \
    get_return_slots_authentication

log = logging.getLogger("rasa-actions")
ServiceType = TypeVar('ServiceType', bound='IResultsService')
T = TypeVar('T', bound='IResultsService')
rasa_to_spring_token = settings.RASA_TO_SPRING_TOKEN

class ActionDynamicFaq(Action):

    def __init__(self, dynamic_service: IResultsService):
        self.dynamic_service = dynamic_service

    def name(self) -> Text:
        return ActionsNome.ACTION_DYNAMIC_FAQ.value

    @handle_action_errors
    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_DYNAMIC_FAQ.value
        full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow_off, intent = get_util_values_with_log(tracker, action_label)

        if tracker.latest_action_name == self.name():
            log_info_text(action_label, f"{BOT_MESSAGES.get('skip_duplication')} - {action_label}")
            return []

        check_is_binded = await get_auth_binding_json(tracker, self.dynamic_service, user_id)

        maintained_intent = intent
        decision_mode, last_intent = get__decision_mode__last_intent(action_label, tracker)
        last_second_question = get_conversational_slots(tracker)

        active_flow_from_semantic = tracker.get_slot("active_flow")

        active_flow, my_entity, my_value = get_active_flow(tracker, action_label, intent, active_flow_from_semantic)

        log.info(f"🚩  Final Values : {my_entity}, Value: {my_value}, intent: {intent}, FLOW: {active_flow}, ORIGINAL-FLOW: {active_flow_off}, id_candidat: {tracker.get_slot('id_candidat')}")
        answer = None

        if intent in ActiveIntents.FINAL_RESULTS_INTENTS and (active_flow == "none" or active_flow is None):
            answer = BOT_MESSAGES.get('no_composante')
            log.info(f"📍  📍  📍  active_flow=NONE : {active_flow}")
            send_message_forwarded_by_buttons(dispatcher, answer)

        else:
            if not check_is_binded:
                log.info("📍  📍  📍  📍  📍  📍  📍  📍  FIRST : - AUTHENTICATION")

                if active_flow == FlowType.DUMMY_FLOW.value:
                    answer = BOT_MESSAGES.get('skip_unrelated_action')
                    log_info_text(action_label, answer)
                    log_info_text("LOLO-1 : ", str(active_flow))

                    context = DynamicToChainContext(
                        tracker=tracker,
                        user_input=user_input,
                        answer=answer,
                        intent=intent,
                        active_flow=active_flow,
                        last_second_question=last_second_question,
                        maintained_intent=maintained_intent,
                        decision_mode=decision_mode,
                    )

                    return from_dynamic_to_chain(context)
                else:
                    answer = await get_message(self.dynamic_service, action_label, active_flow, intent)
                    answer = answer.replace("\\n", "\n")
                    send_message_forwarded_by_buttons(dispatcher, answer)

            else:

                context = ActionContext(
                    user_id=user_id,
                    dispatcher=dispatcher,
                    session_id=session_id,
                    active_flow=active_flow,
                    action_label=action_label,
                    tracker=tracker,
                    user_input=user_input,
                    answer=answer,
                    intent=intent,
                    confidence=confidence
                )


                if active_flow == FlowType.DUMMY_FLOW.value:
                    answer = BOT_MESSAGES.get("skip_unrelated_action")
                    log_info_text(action_label, answer)
                    context = DynamicToChainContext(
                        tracker=tracker,
                        user_input=user_input,
                        answer=answer,
                        intent=intent,
                        active_flow=active_flow,
                        last_second_question=last_second_question,
                        maintained_intent=maintained_intent,
                        decision_mode=decision_mode,
                    )

                    return from_dynamic_to_chain(context)

                answer = await load_authenticated_process(self.dynamic_service, context)

            if decision_mode == 'detailed' and intent == ActiveIntents.NLU_FALLBACK.value:
                maintained_intent = last_intent

        await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        return get_return_slots_authentication(user_roles, tracker.get_slot('id_candidat'), full_name) + get_return_slots_qa_intent_flow_results(user_input, answer, tracker.get_slot("sscomp"), intent, active_flow, last_second_question, maintained_intent, decision_mode)

async def load_authenticated_process(dynamic_service: IResultsService, context: ActionContext):

    user_id = context.user_id
    dispatcher = context.dispatcher
    session_id = context.session_id
    active_flow = context.active_flow
    action_label = context.action_label
    tracker = context.tracker
    user_input = context.user_input
    intent = context.intent
    confidence = context.confidence

    note_sscomp = "note_"
    answer = "No Result Found !"
    log.info("📍  📍  📍  📍  📍  📍  📍  📍  SECOND : + AUTHENTICATION")

    if active_flow and note_sscomp in active_flow:
        log.info(f"📍  📍  active_flow=sscomp : {active_flow} - {tracker.get_slot('id_candidat')}")

        answer_dto = await process_final_results_response(
            dynamic_service,
            active_flow,
            tracker.get_slot("id_candidat"),
            dispatcher,
            tracker,
            confidence,
            get_payload(user_id, session_id, user_input, intent, confidence),
            action_label
        )

        answer = await get_answer_dto(dispatcher, action_label, answer_dto, active_flow)

    elif active_flow not in FlowType.RESULT_FLOWS:
        answer = await get_message(dynamic_service, action_label, active_flow, intent)
        send_message_forwarded_by_buttons(dispatcher, answer)

    else:
        send_message_forwarded_by_buttons(dispatcher, answer)

    return answer

async def get_answer_dto(dispatcher, action_label, answer_dto, active_flow):
    if answer_dto:
        answer = await format_results_message(action_label, answer_dto, active_flow, dispatcher,
                                              json.dumps(answer_dto))
    else:
        answer = BOT_MESSAGES.get("result_not_found", "No result found.")
        send_message_forwarded_by_buttons(dispatcher, answer)
    return answer

async def get_message(dynamic_service: IResultsService, action_label, active_flow, intent):
    log.info(f"📍  📍  active_flow=X : {active_flow}")
    try:
        answer = await dynamic_service.get_faq_by_label_intent(intent)
        log_info_text(action_label, str(answer[:50]))
    except Exception as e:
        answer = BOT_MESSAGES.get('no_response')
        log_exception_text(action_label, e)

    return answer

async def format_results_message(action_label, dto, active_flow, dispatcher, response):
    """Centralized method to format results for the user."""

    all_comp = '_comp'

    log_info_text(action_label, f"all_comp - active_flow : {all_comp} - {active_flow}")
    if not dto['notes'] and not dto.get('allCompNotes'):
        msg_details = follow_no_data_process(dispatcher, active_flow, dto)

    elif dto['notes'] or ((all_comp in active_flow) and dto.get('allCompNotes')):
        log_info_text(action_label, "CASE 2 : NULL or NULL")

        msg_details = get_msg_details(action_label, active_flow, all_comp, dto)

        dispatcher.utter_message(text=msg_details)
        log_info_text(action_label, f"YES : {response[:50]}")
        get_bilan_final_results(dispatcher)

    else:
        msg_details = "No Result Found !"
        dispatcher.utter_message(text=msg_details)

    return msg_details

def get_msg_details(action_label, active_flow, all_comp, dto):
    space = '\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0'
    if (all_comp in active_flow) and dto.get('allCompNotes'):
        log_info_text(action_label, f"GOT IT Composante* : {dto['allCompNotes']}")
        msg_details = BOT_MESSAGES.get('all_comp_mark')

        for k, v in dto['allCompNotes'].items():
            label = str(v['labelAllComp']).strip()
            note = str(v['noteAllComp']).strip()
            msg_details += f"{space}• {label} : {note}\n"
    else:
        log_info_text(action_label, "GOT IT SSComposante")
        msg_details = BOT_MESSAGES.get('sscomp_comp_mark')
        for k, v in dto['notes'].items():
            label = str(v['labelSSComp']).strip()
            note = str(v['noteSSComp']).strip()
            msg_details += f"{space}• {label} : {note}\n"

    return msg_details

def follow_no_data_process(dispatcher, active_flow, dto):

    is_empty_case, msg_prefix = get_is_empty_case(dto, active_flow)

    if is_empty_case:
        msg_details = msg_prefix
        dispatcher.utter_message(text=msg_details)
        get_bilan_final_results(dispatcher)
    else:
        msg_details = BOT_MESSAGES.get('result_not_found')
        send_message_forwarded_by_buttons(dispatcher, msg_details)

    return msg_details

def get_is_empty_case(dto, active_flow):
    msg_prefix = None
    is_empty_case = False
    se_comp_all = 'seq_ens'
    se_sscomp = 'se'
    ptp_comp_all = 'plat_tp'
    ptp_sscomp = 'ptp'
    empty_marks_dto = (not dto['notes']) and (not dto['allCompNotes'])

    if (se_comp_all in active_flow) or (se_sscomp in active_flow):
        msg_prefix = BOT_MESSAGES.get('missed_deposit') + '**Séquence Enseignement** .\n'
        if empty_marks_dto:
            is_empty_case = True

    elif (ptp_comp_all in active_flow) or (ptp_sscomp in active_flow):
        msg_prefix = BOT_MESSAGES.get('missed_deposit') + '**Plateforme de TP** .\n'
        if empty_marks_dto:
            is_empty_case = True

    return is_empty_case, msg_prefix

def from_dynamic_to_chain(context: DynamicToChainContext):

    active_flow = context.active_flow
    events = get_return_slots_qa_intent_flow_results(
        context.user_input,
        context.answer,
        context.tracker.get_slot("sscomp"),
        context.intent,
        active_flow,
        context.last_second_question,
        context.maintained_intent,
        context.decision_mode,
    )
    events.append(FollowupAction("action_lang_chain_routing"))
    events = flatten_events(events)

    log_info_text("LOLO-2 : ", active_flow)
    return events

def get_active_flow(tracker, action_label, intent, active_flow_from_semantic):
    active_flow = "none"
    my_entity = "none"
    my_value = "none"

    simple_flows = {
        ActiveIntents.ASK_RESULTAT_FINAL.value: FlowType.CONGRATS.value,
        ActiveIntents.ASK_STATUS_DELIBERATION_RESULTAT.value: FlowType.DELIBERATION.value,
        ActiveIntents.ASK_ABOUT_CANDIDATURE_PASSAGE_GRADE.value: FlowType.GUIDE_COMP.value,
        ActiveIntents.ASK_CRITERES_EVALUATIONS_SSCOMP.value: FlowType.EVALUATION_GRID.value,
    }

    language_flows = {
        ActiveIntents.ASK_RESULTAT_DISSERTATION.value: {
            "fr": FlowType.NOTE_DISS_FR.value,
            "en": FlowType.NOTE_DISS_EN.value,
        },
        ActiveIntents.ASK_RESULTAT_CAPSULE.value: {
            "fr": FlowType.NOTE_CAPS_FR.value,
            "en": FlowType.NOTE_CAPS_EN.value,
        },
    }

    if intent in simple_flows:
        active_flow = simple_flows[intent]

    elif intent in language_flows:
        language = tracker.get_slot("language")
        active_flow = language_flows[intent].get(language, active_flow)

    elif intent == ActiveIntents.ASK_RESULTAT_SSCOMP.value:
        entities = tracker.latest_message.get("entities", [])
        log_info_text(action_label, entities)

        sscomp = next(
            (
                entity for entity in entities
                if entity.get("entity") == "sscomp"
                and entity.get("extractor") == "DIETClassifier"
            ),
            None,
        )

        if sscomp:
            my_entity = sscomp["entity"]
            my_value = sscomp.get("value", "none")
            active_flow = SSCOMP_TO_FLOW.get(my_value, active_flow)

        log.info(
            "Entity: %s, Value: %s, Flow: %s",
            my_entity,
            my_value,
            active_flow,
        )

    elif intent in ActiveIntents.ALL_ENTRY_INTENTS:
        active_flow = FlowType.DUMMY_FLOW.value

    elif intent == ActiveIntents.ASK_DENY.value:
        active_flow = "None"

    elif intent == ActiveIntents.NLU_FALLBACK.value:
        active_flow = active_flow_from_semantic

    log_info_text("LOLO-00 : ", f"{intent} - {active_flow}")
    return active_flow, my_entity, my_value