"""
actions/entry/entry_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import json
import logging
import time
from typing import Text, Dict, Any, List
from typing import TypeVar

from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import get_payload, get_semantic_random_reply, generate_composante_buttons, \
    get__decision_mode__last_intent, get_local_header, append_friendly_intro_to_answer
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction
from actions.answer_from_file.bot_missions import get_fallback_bot_mission_with_context
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS, ADVICE_PLANNING_BUTTONS, GRILLE_SS_COMPOSANTES, \
    DIRECT_HAND_FLAG
from actions.constants.FlowType import FlowType, INTENT_TO_FLOW
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_with_log, log_debug_text, log_info_text, \
    get_last_conversation
from actions.utils.error_handling import handle_action_errors
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons, \
    send_fallback_problem_to_dsi_forwarded_by_buttons, alert_technical_problem_exception
from actions.utils.slots_helpers import get_conversational_slots, get_return_slots_for_conversations

log = logging.getLogger("rasa-actions")
ServiceType = TypeVar('ServiceType', bound='IResultsService')
T = TypeVar('T', bound='IResultsService')
COMPOSANTES_BUTTONS = generate_composante_buttons()

class ActionGetDynamicResponse(BaseDynamicLLMAction):
    def __init__(self, dynamic_response_service: IResultsService):
        super().__init__()
        self.dynamic_response_service = dynamic_response_service

    def name(self) -> Text:
        return ActionsNome.ACTION_GET_DYNAMIC_RESPONSE.value

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        start_time = time.time()
        action_label = ActionsLabel.PY_DYNAMIC_RESPONSE.value
        username, full_name, user_roles, user_id, session_id, question, last_question, last_answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)
        payload_tech_error = get_payload(user_id, session_id, question, intent, confidence)

        get__decision_mode__last_intent(action_label, tracker)
        log.info(f"🚀 🚀 🚀 🚀 🚀    ENTRY-1  *****>  + {action_label} => {active_flow}")

        if intent != ActiveIntents.ASK_AFFIRM.value:
            active_flow = INTENT_TO_FLOW.get(intent)

        if intent == ActiveIntents.ASK_AFFIRM.value and active_flow == FlowType.GIVE_ADVICE_1.value:
            intent = ActiveIntents.AFFIRM_ADVICE_2.value
            active_flow = INTENT_TO_FLOW.get(intent)

        if intent == ActiveIntents.ASK_AFFIRM.value and active_flow == FlowType.GIVE_ADVICE_2.value:
            intent = ActiveIntents.AFFIRM_ADVICE_3.value
            active_flow = INTENT_TO_FLOW.get(intent)

        if tracker.latest_action_name == self.name():
            log_info_text(action_label, f"{BOT_MESSAGES.get('skip_duplication')} - {action_label}")
            answer = tracker.get_slot('last_answer')
            slots_to_set = {
                "last_last_question": get_conversational_slots(tracker),
                "sscomp": tracker.get_slot("sscomp"),
                "last_question": question,
                "last_answer": answer,
                "active_flow": active_flow,
                "last_intent": tracker.latest_message["intent"]["name"],
                "forward_level": "short"
            }

            log_info_text("PIKA: ", str(slots_to_set))

            return get_return_slots_for_conversations(slots_to_set) # 01-09-2026

        if intent in ActiveIntents.SKIP_FROM_ENTRY_INTENTS:
            log_info_text(action_label, BOT_MESSAGES.get('skip_unrelated_action'))
            return []

        payload = {
            "userInput": question.lower(),
            "intent": intent,
            "userId": user_id
        }

        last_intent = tracker.get_slot("last_intent")
        log_debug_text(action_label, f"Dynamic QA request payload: {payload}")
        log.info(f"🚀 🚀 🚀 🚀 🚀    ENTRY-2  *****>  + {action_label} => {active_flow}")
        log.info(f"🚀 Intent - Last_Intent *****>  + {intent} - {last_intent}")

        try:
            # Step 1: Retrieve candidates from Spring Boot service
            candidates_data = await self.dynamic_response_service.get_dynamic_response(payload)

            if isinstance(candidates_data, str):
                candidates_data = json.loads(candidates_data)

            # Convert to dataclass for type safety
            bot_reply = get_semantic_random_reply(candidates_data, action_label, question)
            log_info_text(action_label, "PIKA-0 : " + bot_reply)

            if intent == FlowType.GREET.value or intent == FlowType.BYE.value:
                dispatcher.utter_message(bot_reply)
                log_info_text(action_label, "PIKA-8")
                log.info(f"{DIRECT_HAND_FLAG}   START WARMING")
                # 2️⃣ Schedule PDF warmup in the background
                # schedule_warmup()
                log.info(f"{DIRECT_HAND_FLAG}   FINISH WARMING")

            elif intent == ActiveIntents.ASK_AFFIRM.value and (last_intent is None or (last_intent and last_intent in ActiveIntents.ALL_CUSTOM_INTENTS)):
                last_last_user_question, last_answer = get_last_conversation(tracker, action_label)
                prompt = get_fallback_bot_mission_with_context(None, question, last_last_user_question, last_answer)
                answer = await self.call_llm_safe(
                    dispatcher=dispatcher,
                    prompt=prompt,
                    action_label=action_label,
                    payload_tech_error=payload_tech_error,
                )

                elapsed = round(time.time() - start_time, 2)
                # {get_local_header(elapsed, 'SECTION-ADV', PDF_PATH)} - {get_local_header(elapsed, 'EVAL-PJ', 'PATH_HIERARCY_EVALS_JURYS_MRKDN')}
                send_multiple_messages_forwarded_by_buttons(dispatcher,f"{get_local_header(elapsed, 'ENTRY', 'LLM')} {append_friendly_intro_to_answer(answer)}", FEEDBACK_BUTTONS)

                await log_chat(user_id, session_id, question, answer, intent, confidence)

                slots_to_set = {
                    "last_last_question": get_conversational_slots(tracker),
                    "sscomp": tracker.get_slot("sscomp"),
                    "last_question": question,
                    "last_answer": answer,
                    "active_flow": active_flow
                }

                log_info_text("🚨 🚨 🚨 🚨 🚨  INTEGRATED : ", str(slots_to_set))
            elif intent == ActiveIntents.ASK_ABOUT_CANDIDATURE_PASSAGE_GRADE.value:
                send_multiple_messages_forwarded_by_buttons(dispatcher, bot_reply, COMPOSANTES_BUTTONS)
                log_info_text(action_label, "PIKA-7")
            elif intent == ActiveIntents.STRESSED_CANDIDAT.value:

                log_info_text(action_label, "azerty : " + question)
                if question == '/stressed_candidat':
                    dispatcher.utter_message(
                        text="👋 Bienvenue dans votre mini guide !\n"
                             "💡 Quelle option souhaitez-vous choisir ?",
                        buttons=ADVICE_PLANNING_BUTTONS
                    )
                else:
                    send_multiple_messages_forwarded_by_buttons(dispatcher, bot_reply, ADVICE_PLANNING_BUTTONS)
                log.info(f"🚀 🚀 🚀  STRESSED_CANDIDAT  -  {ActiveIntents.STRESSED_CANDIDAT.value}")
            elif intent == ActiveIntents.ASK_CRITERES_EVALUATIONS_SSCOMP.value:
                send_multiple_messages_forwarded_by_buttons(dispatcher, bot_reply, GRILLE_SS_COMPOSANTES)
                log.info(f"🚀 🚀 🚀  ASK_CRITERES_EVALUATIONS_SSCOMP  -  {ActiveIntents.ASK_CRITERES_EVALUATIONS_SSCOMP.value}")
            else:
                send_multiple_messages_forwarded_by_buttons(dispatcher, bot_reply, FEEDBACK_BUTTONS)
                slots_to_set = {
                    "last_last_question": get_conversational_slots(tracker),
                    "sscomp": tracker.get_slot("sscomp"),
                    "last_question": question,
                    "last_answer": bot_reply,
                    "active_flow": active_flow
                }

                log_info_text("AZERTY - 1: ", str(slots_to_set))

                log_info_text(action_label, "PIKA-6 : " + bot_reply)

            answer = bot_reply

            slots_to_set = {
                "last_last_question": get_conversational_slots(tracker),
                "sscomp": tracker.get_slot("sscomp"),
                "last_question": question,
                "last_answer": answer,
                "active_flow": active_flow,
                "last_intent": tracker.latest_message["intent"]["name"],
                "forward_level": "short"
            }
            log_info_text("AZERTY - 2: ", str(slots_to_set))

            log_info_text(action_label, "PIKA-5")
            await log_chat(user_id, session_id, question, answer, intent, confidence)

        except CircuitBreakerError as e:
            # ✅ ADD: Handle circuit breaker specifically
            dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))
            answer = alert_technical_problem_exception(action_label, e)
            log_info_text(action_label, "PIKA-4")
            await log_chat(user_id, session_id, question, answer, intent, confidence)

        except KeyError as key_err:
            answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, key_err)
            log_info_text(action_label, "PIKA-3")
            await log_chat(user_id, session_id, question, answer, intent, confidence)

        except (json.JSONDecodeError, TypeError) as parse_err:
            answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, parse_err)
            log_info_text(action_label, "PIKA-2")
            await log_chat(user_id, session_id, question, answer, intent, confidence)

        except Exception as e:
            answer = alert_technical_problem_exception(action_label, e)
            log_info_text(action_label, "PIKA-1")
            await log_chat(user_id, session_id, question, answer, intent, confidence)
            raise

        slots_to_set = {
            "last_last_question": get_conversational_slots(tracker),
            "sscomp": tracker.get_slot("sscomp"),
            "last_question": question,
            "last_answer": answer,
            "active_flow": active_flow,
            "last_intent": tracker.latest_message["intent"]["name"],
            "forward_level": "short"
        }

        log_info_text("AZERTY - 3: ", str(slots_to_set))

        return get_return_slots_for_conversations(slots_to_set)

class ActionGetNextDetails(Action):
    def __init__(self, next_details_response_service: IResultsService):
        self.next_details_response_service = next_details_response_service

    def name(self) -> Text:
        return ActionsNome.ACTION_GET_NEXT_DETAILS_RESPONSE.value

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_GET_NEXT_DETAILS_RESPONSE.value
        username, full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(
            tracker, action_label)
        payload_tech_error = get_payload(user_id, session_id, user_input, intent, confidence)

        log.info(f"🚀 🚀 🚀 🚀 🚀    DETAILS-1  *****>  + {action_label} => {active_flow}")

        payload = {
            "userInput": user_input.lower(),
            "intent": intent,
        }

        log_debug_text(action_label, f"Dynamic QA request payload: {payload}")
        log.info(f"🚀 🚀 🚀 🚀 🚀    DETAILS-2  *****>  + {action_label} => {active_flow}")

        try:
            # Step 1: Retrieve candidates from Spring Boot service
            answer = await self.next_details_response_service.get_next_detailed_response(user_id)
            log_info_text(action_label,f"got : {answer}")
            send_multiple_messages_forwarded_by_buttons(dispatcher, answer, COMPOSANTES_BUTTONS)

            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except CircuitBreakerError as e:
            # ✅ ADD: Handle circuit breaker specifically
            dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))
            answer = alert_technical_problem_exception(action_label, e)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except KeyError as key_err:
            answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error,
                                                                       key_err)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except (json.JSONDecodeError, TypeError) as parse_err:
            answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error,
                                                                       parse_err)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except Exception as e:
            answer = alert_technical_problem_exception(action_label, e)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)
            raise

        return [SlotSet("active_flow", active_flow)]