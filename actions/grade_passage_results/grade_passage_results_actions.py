"""
actions/grade_passage_results/grade_passage_results_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from typing import Text, Dict, Any, List
from typing import TypeVar, TypedDict
from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from actions.actions import get_payload, get_bilan_final_results, classify_results, get__decision_mode__last_intent
from actions.authentication.auth_actions import BaseCredentialsAction
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS
from actions.constants.FlowType import FlowType, SSCOMP_TO_FLOW
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_with_log, resolve_active_flow, log_response_payload, \
    log_info_text, log_info_auth, log_info_expected_flow, \
    log_exception_text
from actions.semantic.semantic_actions import flatten_events
from actions.utils.error_handling import handle_action_errors
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import original_alert_affirm_without_discussion, \
    original_alert_follow_my_proposition, \
    send_multiple_messages_forwarded_by_buttons, send_fallback_problem_to_dsi_forwarded_by_buttons, \
    alert_technical_problem_exception, original_alert_unexpected_response, send_message_forwarded_by_buttons
from actions.utils.slots_helpers import empty_slots, \
    get_return_slots_candidat_id_fullname, \
    get_return_slots_user_jwt_roles, get_conversational_slots, get_return_slots_for_conversations, \
    get_return_slots_qa_intent_flow_results

import json
import logging

log = logging.getLogger("rasa-actions")
ServiceType = TypeVar('ServiceType', bound='IResultsService')
T = TypeVar('T', bound='IResultsService')

class ValidationResult(TypedDict, total=False):
    valid: bool
    full_name: Text
    id_user: int
    jwt: Text
    roles: List[Text]
    username: Text
    password: Text

######################## METHODS NEEDS AUTHENTICATION #########################
class ActionFetchFinalUnitResults(BaseCredentialsAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_DYNAMIC_FINAL_UNIT_RESULTS.value

    def __init__(self, unit_results_service: IResultsService):
        super().__init__(unit_results_service)
        # Initialize with a default flow that can be overridden
        self._expected_flow = "none"

    def expected_flow(self) -> Text:
        """Return the expected flow - uses instance variable set during run()"""
        return self._expected_flow

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # First resolve and store the current flow
        self._expected_flow = resolve_active_flow(tracker)

        # Then proceed with normal credential handling
        return await super().run(dispatcher, tracker, domain)

    async def execute_service_logic(
            self,
            validation: ValidationResult,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_UNIT_RESULTE.value
        username, full_name, user_jwt, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        last_second_question = get_conversational_slots(tracker)
        log_info_expected_flow(action_label,self.expected_flow)
        self._expected_flow = active_flow

        user_jwt = validation.get("jwt")
        user_roles = validation.get("roles", [])
        log_info_auth(action_label, user_roles, user_jwt)

        # Dynamically set expected flow based on intent if needed
        answer_dto = await process_final_results_response(
            self.service,
            active_flow,
            validation['id_user'],
            user_jwt,
            dispatcher,
            tracker,
            confidence,
            get_payload(user_id, session_id, user_input, intent, confidence),
            action_label
        )

        if answer_dto:
            response_dto = await _format_results_message(action_label, answer_dto, active_flow, dispatcher, json.dumps(answer_dto))
            await log_chat(user_id,session_id,user_input,response_dto,intent,confidence)

        slots_to_set = {
            "last_last_question": last_second_question,
            "sscomp": tracker.get_slot("sscomp"),
            "last_question": question,
            "last_answer": answer
        }

        return self.common_slots + get_return_slots_candidat_id_fullname(validation['id_user'], validation['full_name']) + get_return_slots_for_conversations(slots_to_set)

class ActionCongratFinalResults(BaseCredentialsAction):

    def name(self) -> Text:
        return ActionsNome.ACTION_CONGRAT_FINAL_RESULTS.value

    def __init__(self, congrat_service: IResultsService):
        super().__init__(congrat_service)
        self.congrat_service = congrat_service

    # ☠
    def expected_flow(self) -> Text:
        return "congrats"

    async def execute_service_logic(
            self,
            validation: ValidationResult,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_CONGRATS_RESULTS.value
        username, full_name, user_jwt, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)

        if user_jwt and user_roles:
            log_info_auth(action_label, user_roles, user_jwt)

        if validation.get('jwt') and validation['id_user']:
            log_info_auth(action_label, validation['id_user'], validation.get('jwt'))

        id_candidat = validation['id_user']
        try:
            answer = await self.congrat_service.congrat_final_results_by_id_candidat(id_candidat, validation.get('jwt'))
            answer_status = answer.status_code
            bot_response_text = await _get_congrat_results(dispatcher, action_label, answer, answer_status)

        except Exception as e:
            bot_response_text = alert_technical_problem_exception(action_label, e)

        await log_chat(user_id, session_id, user_input, bot_response_text, intent, confidence)

        return self.common_slots + get_return_slots_candidat_id_fullname(id_candidat, validation['full_name'])

################################ FREE METHODS ################################
def from_dynamic_to_chain(tracker, user_input, answer, intent, active_flow, last_second_question, maintained_intent, decision_mode):
    events = get_return_slots_qa_intent_flow_results(user_input, answer, tracker.get_slot("sscomp"), intent, active_flow, last_second_question, maintained_intent, decision_mode)

    events.append(FollowupAction("action_lang_chain_routing"))
    events = flatten_events(events)

    log_info_text("LOLO-2 : ", active_flow)
    return events

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
        username, full_name, user_jwt, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow_off, intent = get_util_values_with_log(tracker, action_label)

        maintained_intent = intent
        decision_mode, last_intent = get__decision_mode__last_intent(action_label, tracker)
        last_second_question = get_conversational_slots(tracker)

        my_entity = "none"
        my_value = "none"
        active_flow = "none"

        active_flow_from_semantic = tracker.get_slot("active_flow")

        if intent == ActiveIntents.ASK_RESULTAT_DISSERTATION.value:
            language = tracker.get_slot("language")  # Get 'fr' or 'en'
            if language == "fr":
                active_flow = FlowType.NOTE_DISS_FR.value
            elif language == "en":
                active_flow = FlowType.NOTE_DISS_EN.value
        elif intent == ActiveIntents.ASK_RESULTAT_CAPSULE.value:
            language = tracker.get_slot("language")  # Get 'fr' or 'en'
            if language == "fr":
                active_flow = FlowType.NOTE_CAPS_FR.value
            elif language == "en":
                active_flow = FlowType.NOTE_CAPS_EN.value
        elif intent == ActiveIntents.ASK_RESULTAT_SSCOMP.value:
            entities = tracker.latest_message.get("entities", [])
            log_info_text(action_label, entities)
            for entity in entities:
                if entity.get("entity") == "sscomp" and entity.get("extractor") == "RegexEntityExtractor":
                    my_entity = entity['entity']
                    my_value = entity['value']
                    log.info(f"ℹ️  Entity: {entity['entity']}, Value: {entity['value']}")
                    if my_entity == "sscomp":
                        active_flow = SSCOMP_TO_FLOW.get(my_value)
                        if active_flow:
                            break
            log.info(f"ℹ️ ........................... Entity: {my_entity}, Value: {my_value}, FLOW: {active_flow}")
        elif intent == ActiveIntents.ASK_RESULTAT_FINAL.value:
            active_flow = FlowType.CONGRATS.value
        elif intent == ActiveIntents.ASK_STATUS_DELIBERATION_RESULTAT.value:
            active_flow = FlowType.DELIBERATION.value
        elif intent == ActiveIntents.ASK_ABOUT_CANDIDATURE_PASSAGE_GRADE.value:
            active_flow = FlowType.GUIDE_COMP.value
        elif intent == ActiveIntents.ASK_CRITERES_EVALUATIONS_SSCOMP.value:
            active_flow = FlowType.EVALUATION_GRID.value
        elif intent in ActiveIntents.ALL_ENTRY_INTENTS: # or str(intent) == str(ActiveIntents.NLU_FALLBACK.value): note prod rdi after comment authentication chatbot
            active_flow = FlowType.DUMMY_FLOW.value
        elif intent == ActiveIntents.ASK_DENY.value:
            active_flow = "None"
        elif str(intent) == str(ActiveIntents.NLU_FALLBACK.value):
            active_flow = active_flow_from_semantic

        #elif str(intent) == str(ActiveIntents.NLU_FALLBACK.value):
            #log_info_text("LOLO-0.0 : ", intent + " - " + ActiveIntents.NLU_FALLBACK.value)
            # active_flow = active_flow_off

        log_info_text("LOLO-00 : ", intent + " - " + ActiveIntents.NLU_FALLBACK.value)
        message_comp_not_found = BOT_MESSAGES.get('no_composante')
        log.info(f"🚩  Final Values : {my_entity}, Value: {my_value}, intent: {intent}, FLOW: {active_flow}, ORIGINAL-FLOW: {active_flow_off}, id_candidat: {tracker.get_slot('id_candidat')}")
        answer = None

        if tracker.latest_action_name == self.name() or (intent == ActiveIntents.NLU_FALLBACK.value and last_intent in ActiveIntents.ALL_LLM_INTENTS_LANG_CHAIN):
            log_info_text(action_label, f"{BOT_MESSAGES.get('skip_duplication')} - {action_label}")
            return []

        if not user_jwt:
            log.info("📍  📍  📍  📍  📍  📍  📍  📍  FIRST : - JWT")
            # if active_flow == "none":
                #     log.info(f"📍  📍  active_flow=NONE : {active_flow}")
                #     answer = message_comp_not_found
            # elif active_flow == FlowType.DUMMY_FLOW.value:
            if active_flow == FlowType.DUMMY_FLOW.value:
                answer = tracker.get_slot("last_answer")
                log_info_text(action_label, BOT_MESSAGES.get('skip_unrelated_action'))
                log_info_text("LOLO-1 : ", active_flow)
                return from_dynamic_to_chain(tracker, user_input, answer, intent, active_flow, last_second_question, maintained_intent, decision_mode)
            else:
                first_answer = await get_message(self, action_label, active_flow, intent)
                answer = first_answer.replace("\\n", "\n")
            send_message_forwarded_by_buttons(dispatcher, answer)
        else:
            note_sscomp = "note_"
            log.info("📍  📍  📍  📍  📍  📍  📍  📍  SECOND : + JWT")

            if active_flow == FlowType.DUMMY_FLOW.value:
                log_info_text(action_label, BOT_MESSAGES.get('skip_unrelated_action'))
                return from_dynamic_to_chain(tracker, user_input, answer, intent, active_flow, last_second_question, maintained_intent, decision_mode)

            if active_flow == "none":
                log.info(f"📍  📍  active_flow=NONE : {active_flow}")
                send_message_forwarded_by_buttons(dispatcher, message_comp_not_found)
            elif active_flow and note_sscomp in active_flow:
                log.info(f"📍  📍  active_flow=sscomp : {active_flow} - {tracker.get_slot('id_candidat')}")

                answer_dto = await process_final_results_response(
                    self.dynamic_service,
                    active_flow,
                    tracker.get_slot("id_candidat"),
                    user_jwt,
                    dispatcher,
                    tracker,
                    confidence,
                    get_payload(user_id, session_id, user_input, intent, confidence),
                    action_label
                )

                if answer_dto:
                    response_dto = await _format_results_message(action_label, answer_dto, active_flow, dispatcher, json.dumps(answer_dto))
                    await log_chat(
                        tracker.sender_id,
                        session_id,
                        tracker.latest_message.get("text"),
                        response_dto,
                        tracker.get_intent_of_latest_message(),
                        confidence
                    )

            elif active_flow == FlowType.CONGRATS.value:
                log.info(f"📍  📍  active_flow=final : {active_flow} - {tracker.get_slot('id_candidat')}")
                try:
                    answerp = await self.dynamic_service.congrat_final_results_by_id_candidat(tracker.get_slot("id_candidat"), user_jwt)

                    answer_status = answerp.status_code
                    answer = await _get_congrat_results(dispatcher, action_label, answerp, answer_status)


                except CircuitBreakerError as e:
                    # ✅ ADD: Handle circuit breaker specifically
                    alert_technical_problem_exception(action_label, e)
                    dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))

                except Exception as e:
                    answer = await get_message(self, action_label, active_flow, intent)
                    send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, get_payload(user_id, session_id, user_input, intent, confidence), e)
            else:
                answer = await get_message(self, action_label, active_flow, intent)
                send_message_forwarded_by_buttons(dispatcher, answer)

        if decision_mode == 'detailed' and intent == ActiveIntents.NLU_FALLBACK.value:
           maintained_intent = last_intent
        await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        return get_return_slots_qa_intent_flow_results(user_input, answer, tracker.get_slot("sscomp"), intent, active_flow, last_second_question, maintained_intent, decision_mode)

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

        username, full_name, user_jwt, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        payload_tech_error = get_payload(user_id, session_id, user_input, intent,confidence)

        intent = tracker.latest_message.get("intent", {}).get("name")
        if intent in ActiveIntents.ALL_ENTRY_INTENTS or intent == ActiveIntents.NLU_FALLBACK.value:
            log_info_text(action_label, BOT_MESSAGES.get('skip_unrelated_action'))
            return get_return_slots_candidat_id_fullname(id_candidat, full_name)

        else:
            try:
                # 1. Slots
                id_candidat = tracker.get_slot('id_candidat')  # NEXT add id_candidat to get_util_values_with_log

                last_intent = tracker.get_slot("last_intent")
                if last_intent:
                    log_info_text(action_label, "##### last_intent = " + last_intent)
                if last_intent and last_intent not in ActiveIntents.NO_AFFIRM_INTENTS:
                    if (
                            (active_flow == "none" or tracker.get_slot('active_flow') == "None")
                            and
                            (intent == "affirm" or tracker.get_intent_of_latest_message() == "affirm")
                    ):
                        bot_response_text = original_alert_affirm_without_discussion()
                        send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text,
                                                                    FEEDBACK_BUTTONS)  # 30-01-2026

                        log_info_text(action_label,
                                      '##### AZERTY : ' + last_intent + '---' + intent + '---' + active_flow)
                        await log_chat(
                            user_id,
                            session_id,
                            user_input,
                            bot_response_text,
                            tracker.get_intent_of_latest_message(),
                            confidence
                        )
                        return empty_slots()
                # else:
                    # send_multiple_messages_forwarded_by_buttons(dispatcher, BOT_MESSAGES.get("affirm_no_result"), FEEDBACK_BUTTONS)

                # 3. Handle flow
                if last_intent and last_intent in ActiveIntents.NO_AFFIRM_INTENTS:
                    if id_candidat:
                        if active_flow in FlowType._value2member_map_:
                            bot_response_text = await self._process_results(dispatcher, action_label, id_candidat,
                                                                            full_name, tracker, payload_tech_error)
                        else:
                            bot_response_text = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label,
                                                                                                  payload_tech_error,
                                                                                                  f'Flux Inexistant : {active_flow}')
                    else:
                        bot_response_text = BOT_MESSAGES.get('not_connected')
                        send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text, FEEDBACK_BUTTONS)
                else:
                    bot_response_text = BOT_MESSAGES.get('affirm_no_result')
                    send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text, FEEDBACK_BUTTONS)

            except Exception as e:
                bot_response_text = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label,
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

    async def _process_results(self, dispatcher, action_label, id_candidat, full_name, tracker, payload_tech_error):

        try:
            answer = await self.results_service.get_candidate_results(id_candidat, tracker.get_slot("jwt"))
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
            full_answer = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, e)

        return full_answer

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
        username, full_name, user_jwt, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        last_intent = tracker.get_slot("last_intent")

        log_info_text(action_label, "##### active_flow = " + active_flow)
        log_info_text(action_label, "##### last_intent = " + last_intent)

        if last_intent in ActiveIntents.NO_AFFIRM_INTENTS:
            log_info_text(action_label, "##### active_flow 0 = " + active_flow)
            if active_flow is not None and str(active_flow) != "none":
                if intent == "provide_credentials":
                    log_info_text(action_label, "##### active_flow 1 = " + active_flow)
                    bot_response_text = BOT_MESSAGES.get('confirm_before_auth')
                    send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text, FEEDBACK_BUTTONS)
                    await log_chat(user_id, session_id, user_input, bot_response_text, intent, confidence)
                    return [SlotSet("active_flow", FlowType.DELIBERATION.value)]

                elif intent == "affirm":
                    log_info_text(action_label,
                                  "##### active_flow 2 = " + active_flow + ' -- ' + last_intent + ' -- ' + intent)
                    if not user_jwt:
                        bot_response_text = BOT_MESSAGES.get('give_your_credentials')
                        send_multiple_messages_forwarded_by_buttons(dispatcher, bot_response_text, FEEDBACK_BUTTONS)
                    else:
                        try:
                            answer = await self.deliberation_service.congrat_final_results_by_id_candidat(
                                tracker.get_slot("id_candidat"), user_jwt)
                            answer_status = answer.status_code
                            bot_response_text = await _get_congrat_results(dispatcher, action_label, answer,
                                                                           answer_status)

                        except Exception as e:
                            bot_response_text = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher,
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
        #else:
        #    log_info_text(action_label, "##### active_flow 4 = " + str(active_flow))
        #    send_multiple_messages_forwarded_by_buttons(dispatcher, BOT_MESSAGES.get("affirm_no_result"), FEEDBACK_BUTTONS)
        return get_return_slots_user_jwt_roles(user_jwt, user_roles)

################################ COMMON METHODS ################################
def get_bilan_header(full_name, applied_grade, moyenne_totale, score_totale):
    return [
        "📊 **Bilan Global**",
        f"👤 {full_name or 'N/A'}",
        f"🏆 **Grade Postulé** : {applied_grade}",
        f"💯 **Score Total : {moyenne_totale} / {score_totale}**",
        ""
    ]

async def get_message(self, action_label, active_flow, intent):
    log.info(f"📍  📍  active_flow=X : {active_flow}")
    try:
        answer = await self.dynamic_service.get_faq_by_label_intent(intent)
        log_info_text(action_label, answer[:50])
    except Exception as e:
        answer = BOT_MESSAGES.get('no_response')
        log_exception_text(action_label, e)

    return answer

async def process_final_results_response(
        service: IResultsService,
        active_flow: str,
        user_id: int,
        jwt: str,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        confidence: float,
        payload_tech_error: dict,
        action_label: str
) -> Any:
    """Call backend for final results and handle all response cases."""
    try:
        answer = await service.find_final_results_for_bot_by_intent_and_candidat_id(
            active_flow,
            user_id,
            jwt,
        )

        answer_status = answer.status_code
        log_info_text(action_label, f"answer_status : {answer_status} - {active_flow}")

        if answer_status == 403:
            response = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, answer.text)

        elif answer_status == 404:
            response = answer.text
            dispatcher.utter_message(response)

        elif answer_status == 200:
            response = answer.text
            dto = json.loads(response) if isinstance(response, str) else response
            log_info_text(action_label, f"ℹ️  A dto : {dto}")
            log_info_text(action_label, f"ℹ️  B dto-ssComp : {dto.get('notes')}")
            log_info_text(action_label, f"ℹ️  C dto-allComp : {dto.get('allCompNotes')}")
            return dto

        elif answer_status == 500:
            error_data = answer.json()
            error_text = f"Server error: {error_data.get('error', 'Erreur inconnue')}"
            response = alert_technical_problem_exception(action_label, error_text)

            if active_flow == FlowType.DELIBERATION.value:
                msg = original_alert_follow_my_proposition()
            else:
                msg = original_alert_unexpected_response()
            dispatcher.utter_message(msg)

        else:
            error_data = answer.json()
            error_text = f"Server error: {error_data.get('error', 'Erreur inconnue')}"
            response = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, error_text)

    except CircuitBreakerError as e:
        # ✅ ADD: Handle circuit breaker specifically
        response = alert_technical_problem_exception(action_label, e)
        dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))

    except Exception as e:
        response = send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, e)

    # log user interaction
    await log_chat(
        tracker.sender_id,
        tracker.get_slot("session_id"),
        tracker.latest_message.get("text"),
        response,
        tracker.get_intent_of_latest_message(),
        confidence,
    )

    return None

async def _format_results_message(action_label, dto, active_flow, dispatcher, response):
    """Centralized method to format results for the user."""
    msg_prefix = None
    msg_details = None
    is_empty_case = False
    all_comp = '_comp'
    se_comp_all = 'seq_ens'
    se_sscomp = 'se'
    ptp_comp_all = 'plat_tp'
    ptp_sscomp = 'ptp'
    empty_marks_dto = (not dto['notes']) and (not dto['allCompNotes'])
    space = '\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0'

    log_info_text(action_label, f"all_comp - active_flow : {all_comp} - {active_flow}")
    if not dto['notes'] and not dto.get('allCompNotes'):
        if (se_comp_all in active_flow) or (se_sscomp in active_flow):
            msg_prefix = BOT_MESSAGES.get('missed_deposit') + '**Séquence Enseignement** .\n'
            if empty_marks_dto:
                is_empty_case = True

        elif (ptp_comp_all in active_flow) or (ptp_sscomp in active_flow):
            msg_prefix = BOT_MESSAGES.get('missed_deposit') + '**Plateforme de TP** .\n'
            if empty_marks_dto:
                is_empty_case = True
        if is_empty_case:
            msg_details = msg_prefix
            dispatcher.utter_message(text=msg_details)
            get_bilan_final_results(dispatcher)
        else:
            msg_prediction = BOT_MESSAGES.get('result_not_found')
            send_message_forwarded_by_buttons(dispatcher, msg_prediction)

    elif dto['notes'] or ((all_comp in active_flow) and dto.get('allCompNotes')):
        log_info_text(action_label, "CASE 2 : NULL or NULL")
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
        dispatcher.utter_message(text=msg_details)
        log_info_text(action_label, f"YES : {response[:50]}")
        get_bilan_final_results(dispatcher)

    return msg_details

async def _get_congrat_results(dispatcher, action_label, answer, answer_status):
    """
       Handle the response from a service call and send messages via dispatcher.

       :param answer_status:
       :param action_label: Identifier for logging
       :param dispatcher: Rasa dispatcher for bot replies
       :param answer: Response object from the service
       :return: The text sent to the user (bot_response_text)
       """

    log_info_text(action_label, f"answer_status : {answer_status}")

    if answer_status == 403:
        bot_response_text = BOT_MESSAGES.get('not_authorized_user')
        log_response_payload(action_label, answer_status, bot_response_text)
        dispatcher.utter_message(bot_response_text)

    elif answer_status == 404:
        bot_response_text = answer.text
        log_response_payload(action_label, answer_status, bot_response_text)
        dispatcher.utter_message(bot_response_text)

    elif answer_status == 200:
        bot_response_text = answer.text
        log_response_payload(action_label, answer_status, bot_response_text)
        dto = json.loads(bot_response_text) if isinstance(bot_response_text, str) else bot_response_text
        log_info_text(action_label, bot_response_text)
        await _handle_decision(dispatcher, dto)

    elif answer_status == 500:
        error_data = answer.json()
        # Log the detailed error but show a generic message to users
        response = f"Server error: {error_data.get('error', 'Erreur inconnue')}"
        bot_response_text = BOT_MESSAGES.get('technical_problem_error')
        log_response_payload(action_label, answer_status, bot_response_text + response)
        dispatcher.utter_message(bot_response_text)

    else:
        bot_response_text = BOT_MESSAGES.get('unexpected_error')
        log_response_payload(action_label, answer_status, bot_response_text)
        dispatcher.utter_message(bot_response_text)

    return bot_response_text

async def _handle_decision(dispatcher, dto: dict):
    if dto.get("decisionCPGR"):
        dispatcher.utter_message(text=dto['messageText'], image=dto['cardURL'])
        get_bilan_final_results(dispatcher)
    else:
        send_message_forwarded_by_buttons(dispatcher, dto['messageText'])

