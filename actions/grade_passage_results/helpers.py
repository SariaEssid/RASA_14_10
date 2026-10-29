"""
actions/grade_passage_results/helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import json
from typing import Any

import httpx
from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.constants.Constants import BOT_MESSAGES
from actions.constants.FlowType import FlowType
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import log_info_text, log_response_payload
from actions.settings.settings import settings
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import send_message_forwarded_by_buttons, \
    send_fallback_problem_to_dsi_forwarded_by_buttons, alert_technical_problem_exception, \
    original_alert_follow_my_proposition, original_alert_unexpected_response

rasa_to_spring_token = settings.RASA_TO_SPRING_TOKEN


def get_candidate_id(tracker):
    log_info_text("PPPPP : ", tracker.get_slot('last_intent'))
    log_info_text("id_candidat : ", tracker.get_slot('id_candidat'))
    log_info_text("full_name : ", tracker.get_slot('full_name'))
    return tracker.get_slot("id_candidat")

def get_candidate_details(tracker):
    log_info_text("PPPPP : ", tracker.get_slot('last_intent'))
    log_info_text("id_candidat : ", tracker.get_slot('id_candidat'))
    log_info_text("full_name : ", tracker.get_slot('full_name'))
    return tracker.get_slot("id_candidat"), tracker.get_slot('full_name')

def get_bilan_final_results(dispatcher):
    msg_prediction = ("💡Si vous voulez, je peux vous fournir le résultat final complet.\n"
                      "Juste tapez : **Oui**, et je vous pésenterai un bilan détaillé de vos notes.🚀")
    send_message_forwarded_by_buttons(dispatcher, msg_prediction)

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


async def get_auth_binding_json(
    tracker: Tracker,
    service: IResultsService,
    user_id
):
    # Clear any previously stored identity before validating a new binding.
    tracker.slots["id_candidat"] = None
    tracker.slots["full_name"] = None

    try:
        auth_binding_data = await service.get_chat_session_identity(
            {"senderId": user_id},
            rasa_to_spring_token
        )
    except (httpx.HTTPError, TimeoutError):
        return None

    # Accept either a JSON string or an already-parsed dictionary.
    if isinstance(auth_binding_data, str):
        try:
            auth_binding_json = json.loads(auth_binding_data)
        except json.JSONDecodeError:
            return None

    elif isinstance(auth_binding_data, dict):
        auth_binding_json = auth_binding_data

    else:
        return None

    # The response must be a dictionary containing a non-empty userId.
    if not isinstance(auth_binding_json, dict):
        return None

    bound_user_id = auth_binding_json.get("userId")

    if bound_user_id is None or not str(bound_user_id).strip():
        return None

    # Populate identity slots only after validation succeeds.
    tracker.slots["id_candidat"] = bound_user_id
    tracker.slots["full_name"] = auth_binding_json.get("fullName")

    return auth_binding_json


async def _handle_decision(dispatcher, dto: dict):
    if dto.get("decisionCPGR"):
        dispatcher.utter_message(text=dto['messageText'], image=dto['cardURL'])
        get_bilan_final_results(dispatcher)
    else:
        send_message_forwarded_by_buttons(dispatcher, dto['messageText'])


async def process_final_results_response(
        service: IResultsService,
        active_flow: str,
        user_id: int,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        confidence: float,
        payload_tech_error: dict,
        action_label: str
) -> Any:
    """Call backend for final results and handle all response cases."""
    try:

        log_info_text(action_label, f"user_id : {user_id}")
        id_candidat = get_candidate_id(tracker)

        response = ""
        if id_candidat:
            answer = await service.find_final_results_for_bot_by_intent_and_candidat_id(
                active_flow,
                id_candidat,
                rasa_to_spring_token,
            )

            answer_status = answer.status_code
            log_info_text(action_label, f"answer_status : {answer_status} - {active_flow}")

            if answer_status == 403:
                response = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, answer.text)

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
                response = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, error_text)

    except CircuitBreakerError as e:
        # ✅ ADD: Handle circuit breaker specifically
        response = alert_technical_problem_exception(action_label, e)
        dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))

    except Exception as e:
        response = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, e)

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
