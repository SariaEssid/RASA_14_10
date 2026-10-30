"""
actions/grade_passage_results/grade_passage_results_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import json
import logging
from typing import Text, Dict, Any, List
from typing import TypeVar

from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import get_payload
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS
from actions.constants.FlowType import FlowType
from actions.grade_passage_results.data_classes import FlowCheckContext, GetResponseContext
from actions.grade_passage_results.helpers import get_candidate_details, get_candidate_id, _get_congrat_results, \
    get_auth_binding_json
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_with_log, log_info_text, log_exception_text
from actions.settings.settings import settings
from actions.utils.error_handling import handle_action_errors
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import original_alert_affirm_without_discussion, \
    send_multiple_messages_forwarded_by_buttons, send_fallback_problem_to_dsi_forwarded_by_buttons, \
    alert_technical_problem_exception, original_alert_unexpected_response, send_message_forwarded_by_buttons
from actions.utils.slots_helpers import empty_slots, \
    get_return_slots_candidat_id_fullname, \
    get_return_slots_user_fullname_roles, get_return_slots_for_conversations, \
    get_return_slots_qa_intent_flow_results

log = logging.getLogger("rasa-actions")
ServiceType = TypeVar('ServiceType', bound='IResultsService')
T = TypeVar('T', bound='IResultsService')
rasa_to_spring_token = settings.RASA_TO_SPRING_TOKEN

######################## METHODS NOT STILL NEEDING AUTHENTICATION #########################
class ActionFetchFinalUnitResults(Action):

    def __init__(self, unit_results_service: IResultsService):
        self.unit_results_service = unit_results_service

    def name(self) -> Text:
        return ActionsNome.ACTION_DYNAMIC_FINAL_UNIT_RESULTS.value

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_UNIT_RESULTE.value
        full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(
            tracker, action_label)

        bound = await get_auth_binding_json(tracker, self.unit_results_service, user_id)
        if not bound:
            dispatcher.utter_message(text=BOT_MESSAGES.get("login_required"),
                                     json_message={"type": "auth_required"})
            return get_return_slots_candidat_id_fullname(None, None)
        return []

class ActionCongratFinalResults(Action):

    def __init__(self, congrat_service: IResultsService):
        self.congrat_service = congrat_service

    def name(self) -> Text:
        return ActionsNome.ACTION_CONGRAT_FINAL_RESULTS.value

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_CONGRATS_RESULTS.value
        full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)

        if tracker.latest_action_name == self.name():
            log_info_text(action_label, f"{BOT_MESSAGES.get('skip_duplication')} - {action_label}")
            return []

        await get_auth_binding_json(tracker, self.congrat_service, user_id)

        id_candidat = get_candidate_id(tracker)

        if id_candidat:
            try:
                log_info_text("PIKATCHU 1 : ", id_candidat + " - " + active_flow)

                answer = await self.congrat_service.congrat_final_results_by_id_candidat(id_candidat, rasa_to_spring_token)
                answer_status = answer.status_code
                bot_response_text = await _get_congrat_results(dispatcher, action_label, answer, answer_status)

            except Exception as e:
                bot_response_text = alert_technical_problem_exception(action_label, e)
        else:
            bot_response_text = BOT_MESSAGES.get("login_required")

        await log_chat(user_id, session_id, user_input, bot_response_text, intent, confidence)

        tracker.slots["active_flow"] = FlowType.ALL_BILAN.value
        log_info_text("active_flow 111 : ", tracker.get_slot("active_flow"))
        return get_return_slots_candidat_id_fullname(id_candidat, full_name) + get_return_slots_for_conversations({ "active_flow": FlowType.ALL_BILAN.value })

################################ FREE METHODS ################################

def get_dynamic_events(tracker, user_input, answer, intent, active_flow, last_second_question, maintained_intent, decision_mode):
    events = get_return_slots_qa_intent_flow_results(user_input, answer, tracker.get_slot("sscomp"), intent, active_flow, last_second_question, maintained_intent, decision_mode)

    log_info_text("LOLO-2 : ", active_flow)
    return events

class ActionHandleDynamicFinalGlobalResults(Action):
    VALID_FLOWS = {f.value for f in FlowType}

    def __init__(self, results_service: IResultsService):
        self.results_service = results_service

    def name(self) -> Text:
        return ActionsNome.ACTION_BILAN_FINAL_RESULTS.value

    @handle_action_errors
    async def run(self, dispatcher, tracker, domain):
        action_label = ActionsLabel.PY_GLOBAL_RESULTS.value
        id_candidat=None

        full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        payload_tech_error = get_payload(user_id, session_id, user_input, intent,confidence)

        intent = tracker.latest_message.get("intent", {}).get("name")
        if intent in ActiveIntents.ALL_ENTRY_INTENTS or intent == ActiveIntents.NLU_FALLBACK.value:
            log_info_text(action_label, BOT_MESSAGES.get('skip_unrelated_action'))
            return get_return_slots_candidat_id_fullname(id_candidat, full_name)

        else:
            try:
                # 1. Slots
                bound = await get_auth_binding_json(tracker, self.results_service, user_id) # jdida

                if not bound:
                    dispatcher.utter_message(
                        text=BOT_MESSAGES.get("login_required"),
                        json_message={"type": "auth_required"},
                    )
                    return get_return_slots_candidat_id_fullname(None, None)

                id_candidat = get_candidate_id(tracker)  # NEXT add id_candidat to get_util_values_with_log
                last_intent = tracker.get_slot("last_intent")

                context = FlowCheckContext(
                    dispatcher=dispatcher,
                    tracker=tracker,
                    action_label=action_label,
                    last_intent=last_intent,
                    intent=intent,
                    active_flow=active_flow,
                    user_id=user_id,
                    session_id=session_id,
                    user_input=user_input,
                    confidence=confidence,
                )

                slots = await self._process_verif_flow(context)
                if slots is not None:
                    return slots

                # 3. Handle flow
                context = GetResponseContext(
                    dispatcher=dispatcher,
                    tracker=tracker,
                    action_label=action_label,
                    last_intent=last_intent,
                    active_flow=active_flow,
                    payload_tech_error=payload_tech_error
                )

                bot_response_text = await self._get_bot_response_text(context)

            except Exception as e:
                bot_response_text = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label,
                                                                                      payload_tech_error, e)

            await log_chat(
                user_id,
                session_id,
                user_input,
                bot_response_text,
                tracker.get_intent_of_latest_message(),
                confidence
            )
            return get_return_slots_candidat_id_fullname(id_candidat, full_name)

    async def _process_results(self, dispatcher, action_label, tracker, payload_tech_error):

        try:
            id_candidat, full_name = get_candidate_details(tracker)
            log_info_text("GLOBAL - id_candidat", id_candidat + " - " + full_name)

            answer = await self.results_service.get_candidate_results(id_candidat, rasa_to_spring_token)
            results = json.loads(answer) if isinstance(answer, str) else answer

            applied_grade = results.get('appliedGrade', 'N/A')
            moyenne_totale = results.get('moyenneTotale', 'N/A')
            score_totale = results.get('scoreTotale', 'N/A')

            message = get_bilan_header(full_name, applied_grade, moyenne_totale, score_totale)

            hierarchy = classify_results(results)
            for component, data in hierarchy.items():
                message.append(f"**{component} : {data.get('total', 'N/A')} / {data.get('bareme', 'N/A')}**")
                self._add_component_details(action_label,message, data, 1)
                message.append("")

            full_answer = "\n".join(message)
            dispatcher.utter_message(text="\n".join(message))
            send_message_forwarded_by_buttons(dispatcher, BOT_MESSAGES.get('good_reception'))

        except CircuitBreakerError as e:
            # ✅ ADD: Handle circuit breaker specifically
            full_answer = alert_technical_problem_exception(action_label, e)
            dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))

        except Exception as e:
            full_answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, e)

        return full_answer

    async def _get_bot_response_text(self, context: GetResponseContext):

        dispatcher = context.dispatcher
        tracker = context.tracker
        last_intent = context.last_intent
        active_flow = context.active_flow
        payload_tech_error = context.payload_tech_error
        action_label = context.action_label

        if last_intent and last_intent in ActiveIntents.NO_AFFIRM_INTENTS:
            if active_flow in FlowType._value2member_map_:
                bot_response_text = await self._process_results(dispatcher, action_label, tracker, payload_tech_error)
            else:
                bot_response_text = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label,
                                                                                            payload_tech_error,
                                                                                            f'Flux Inexistant : {active_flow}')
        else:
            bot_response_text = BOT_MESSAGES.get('affirm_no_result')
            send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text, FEEDBACK_BUTTONS)
        return bot_response_text

    @staticmethod
    async def _process_verif_flow(context: FlowCheckContext):

        tracker = context.tracker
        last_intent = context.last_intent
        active_flow = context.active_flow
        intent = context.intent

        if last_intent and last_intent not in ActiveIntents.NO_AFFIRM_INTENTS:
            if (
                    (active_flow == "none" or tracker.get_slot('active_flow') == "None")
                    and
                    (intent == "affirm" or tracker.get_intent_of_latest_message() == "affirm")
            ):
                bot_response_text = original_alert_affirm_without_discussion()
                send_multiple_messages_forwarded_by_buttons(context.dispatcher, bot_response_text,
                                                            FEEDBACK_BUTTONS)  # 30-01-2026

                log_info_text(context.action_label, '##### AZERTY : ' + last_intent + '---' + str(intent) + '---' + str(active_flow))
                await log_chat(
                    context.user_id,
                    context.session_id,
                    context.user_input,
                    bot_response_text,
                    tracker.get_intent_of_latest_message(),
                    context.confidence
                )
                return empty_slots()
        return None

    def _add_component_details(self, action_label, message, component_data, level):
        comp_level = None
        try:
            comp_level = "\u00A0\u00A0\u00A0\u00A0" * level
            bullet = {1: "•", 2: "◦", 3: "▪"}.get(level, "▫")

            for key, item in component_data.items():
                if key == "total":
                    continue
                if isinstance(item, dict) and "name" in item:
                    message.append(f"{comp_level}{bullet} {item['name']} : "
                                   f"*{item.get('score', 'N/A')} / {item.get('bareme', 'N/A')}*")
                    for sub_key, sub_item in item.items():
                        if sub_key not in ["name", "score"] and isinstance(sub_item, dict):
                            self._add_component_details(action_label, message, {sub_key: sub_item}, level + 1)
        except Exception as e:
            log_exception_text(action_label, e)
            message.append(f"{comp_level}⚠️ Détails incomplets")

class ActionHandleDeliberationFinalResults(Action):
    def __init__(self, deliberation_service: IResultsService):
        self.deliberation_service = deliberation_service

    def name(self) -> Text:
        return ActionsNome.ACTION_DELIBERATION_FINAL_RESULTS.value

    @handle_action_errors
    async def run(self, dispatcher, tracker, domain):

        action_label = ActionsLabel.PY_DELIBERATION.value
        full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        last_intent = tracker.get_slot("last_intent")

        log_info_text(action_label, "##### active_flow = " + active_flow)
        log_info_text(action_label, "##### last_intent = " + last_intent)

        if last_intent in ActiveIntents.NO_AFFIRM_INTENTS:
            log_info_text(action_label, "##### active_flow 0 = " + active_flow)
            if active_flow is not None and str(active_flow) != "none":

                id_candidat = get_candidate_id(tracker)
                log_info_text("LOLO-3 id_candidat : ", id_candidat)
                if intent == "affirm":

                    log_info_text(action_label, "##### active_flow 2 = " + active_flow + ' -- ' + last_intent + ' -- ' + intent)
                    if not rasa_to_spring_token or not id_candidat:
                        bot_response_text = BOT_MESSAGES.get('login_required')
                        send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text, FEEDBACK_BUTTONS)
                    else:
                        try:
                            log_info_text("PIKATCHU 2 : ", id_candidat + " - " + active_flow)
                            answer = await self.deliberation_service.congrat_final_results_by_id_candidat(id_candidat, rasa_to_spring_token)
                            answer_status = answer.status_code
                            bot_response_text = await _get_congrat_results(dispatcher, action_label, answer, answer_status)

                        except Exception as e:
                            bot_response_text = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher,
                                                                                                  action_label,
                                                                                                  get_payload(user_id,
                                                                                                              session_id,
                                                                                                              user_input,
                                                                                                              intent,
                                                                                                              confidence),
                                                                                                  e)

                    await log_chat(user_id, session_id, user_input, bot_response_text, intent, confidence)
                    return [SlotSet("active_flow", FlowType.CONGRATS.value)]

                else:
                    # fallback par défaut
                    log_info_text(action_label, "##### active_flow 3 = " + active_flow)
                    bot_response_text = original_alert_unexpected_response()
                    dispatcher.utter_message(bot_response_text)

                await log_chat(user_id, session_id, user_input, bot_response_text, intent, confidence)
        return get_return_slots_user_fullname_roles(full_name, user_roles)

def classify_results(results):
    hierarchy = {}

    # first, add the main components (1, 2, 3…)
    for comp_id, comp_data in results["allCompNotes"].items():
        comp_name = comp_data["labelAllComp"]
        hierarchy[comp_name] = {
            "total": comp_data["noteAllComp"],
            "bareme": comp_data["baremeAllComp"]
        }

    # then, add the subnotes dynamically
    for note_id, note_data in results["notes"].items():
        for comp_id, comp_data in results["allCompNotes"].items():
            if note_id.startswith(comp_id) and note_id != comp_id:  # ✅ skip "1", "2", "3"
                comp_name = comp_data["labelAllComp"]
                current = hierarchy[comp_name]

                # progressively build tree (e.g. 21211 → 21 → 212 → 2121 → 21211)
                for i in range(len(comp_id), len(note_id) + 1):
                    sub_id = note_id[:i]
                    if sub_id == comp_id:  # ✅ don’t try to fetch "2"
                        continue
                    subnote = safe_get_note(results["notes"], sub_id)
                    if subnote and sub_id not in current:
                        current[sub_id] = subnote
                    current = current[sub_id]
    return hierarchy

def safe_get_note(notes, key):
    if key not in notes:
        return None
    return {
        "name": notes[key].get("labelSSComp"),
        "score": notes[key].get("noteSSComp"),
        "bareme": notes[key].get("baremeSSComp")
    }

def get_bilan_header(full_name, applied_grade, moyenne_totale, score_totale):
    return [
        "📊 **Bilan Global**",
        f"👤 **Candidat(e)** : {full_name or 'N/A'}",
        f"🏆 **Grade Postulé** : {applied_grade}",
        f"💯 **Score Total : {moyenne_totale} / {score_totale}**",
        ""
    ]

