"""
actions/tutorials/tutorials_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from io import BytesIO
from typing import Text, Dict, Any, List
from typing import TypeVar
from PIL import Image
from aiocircuitbreaker import CircuitBreakerError
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from actions.actions import get_payload, get_semantic_random_reply, generate_composante_buttons
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.Constants import BOT_MESSAGES, GRILLE_SS_COMPOSANTES
from actions.constants.FlowType import INTENT_TO_FLOW, FlowType
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_with_log, log_info_text
from actions.settings.settings import settings
from actions.utils.error_handling import handle_action_errors
from actions.utils.interfaces import IResultsService
from actions.utils.message_helpers import send_fallback_problem_to_dsi_forwarded_by_buttons, \
    alert_technical_problem_exception, send_multiple_messages_forwarded_by_buttons, \
    send_multiple_messages_images_forwarded_by_buttons, send_custom_fallback_problem_to_dsi_forwarded_by_buttons
from actions.utils.slots_helpers import empty_slots

import requests
import base64
import json
import logging
import re

log = logging.getLogger("rasa-actions")
ServiceType = TypeVar('ServiceType', bound='IResultsService')
T = TypeVar('T', bound='IResultsService')

COMPOSANTES_BUTTONS = generate_composante_buttons()

class ActionSelectButton(Action):
    def __init__(self, select_composante: IResultsService):
        self.select_composante = select_composante

    def name(self) -> Text:
        return ActionsNome.ACTION_SELECT_BUTTON.value

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        action_label = ActionsLabel.PY_SELECT_BUTTON.value
        username, full_name, user_roles, user_id, session_id, user_input, question, answer, confidence, active_flow, intent = get_util_values_with_log(tracker, action_label)

        payload_tech_error = get_payload(user_id, session_id, user_input, intent[:100], confidence)

        try:
            BUTTONS_TO_BE_SELECTED : list[dict]



            final_active_flow = INTENT_TO_FLOW.get(intent)
            selected_button = _get_selected_button_kind_from_active_flow(tracker, final_active_flow)
            log.info(f"🚀 🚀 🚀 🚀 🚀   selected_button :  + {action_label} => {final_active_flow} : {active_flow} - {selected_button}")

            payload = {
                "userInput": selected_button,
                "intent": intent,
                "userId": user_id
            }

            # Step 1: Retrieve candidates from Spring Boot service
            candidates_data = await self.select_composante.get_info_by_button_label(payload)
            if isinstance(candidates_data, str):
                candidates_data = json.loads(candidates_data)

            bot_reply = get_semantic_random_reply(candidates_data, action_label, user_input)

            log_info_text(action_label, bot_reply)

            ############################################################################################################)

            if active_flow == FlowType.GUIDE_COMP.value:
                send_multiple_messages_forwarded_by_buttons(dispatcher, bot_reply, COMPOSANTES_BUTTONS)

            elif active_flow == FlowType.EVALUATION_GRID.value:
                # 1️⃣ Find all Google Drive file IDs
                matches = re.findall(r'/d/([a-zA-Z0-9_-]+)', bot_reply)
                if not matches:
                    answer = BOT_MESSAGES.get("no_eval_grid_exist") + BOT_MESSAGES.get("want_to_know_more")
                    send_multiple_messages_forwarded_by_buttons(dispatcher, answer, GRILLE_SS_COMPOSANTES)
                    await log_chat(user_id, session_id, user_input, answer, intent, confidence)
                    return []

                # 2️⃣ Loop through each file ID and convert to base64
                list_img_str = await get_google_images(matches, dispatcher, action_label, payload_tech_error, user_id, session_id, user_input, intent, confidence)

                # 3️⃣ Send all images at once with buttons
                if list_img_str:
                    answer = bot_reply
                    post_fix_msg = BOT_MESSAGES.get("want_to_know_more")
                    send_multiple_messages_images_forwarded_by_buttons(dispatcher, answer, list_img_str,
                                                                       GRILLE_SS_COMPOSANTES, post_fix_msg)


            else:
                answer = "NO ACTIVE FLOW DETECTED !"

            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except CircuitBreakerError as e:
            # ✅ ADD: Handle circuit breaker specifically
            dispatcher.utter_message(BOT_MESSAGES.get('circuit_opened_alert'))
            answer = alert_technical_problem_exception(action_label, e)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except KeyError as key_err:
            answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, key_err)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except (json.JSONDecodeError, TypeError) as parse_err:
            answer = await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, parse_err)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

        except Exception as e:
            answer = alert_technical_problem_exception(action_label, e)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)
            raise

        return empty_slots()

def _get_selected_button_kind_from_active_flow(tracker, active_flow):
    if active_flow == 'selected_comp':
        return _get_indexer(tracker, "sscomp")
    elif active_flow == 'selected_advice_plan':
        return _get_indexer(tracker, "goto")
    else:
        return None

def _get_indexer(tracker, indexer):
    return next(tracker.get_latest_entity_values(indexer), None)

async def get_google_images(matches, dispatcher, action_label, payload_tech_error, user_id, session_id, user_input, intent, confidence):
    list_img_str = []
    for file_id in matches:
        download_url = f"{settings.DRIVE_LINK}={file_id}"
        try:
            response = requests.get(download_url)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content)).convert("RGB")
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            list_img_str.append(img_str)

        except Exception as e:
            message = "Oupsy ! 😬, le lien est inaccessible actuellement !\n" + BOT_MESSAGES.get('to_be_fixed_by_team')
            answer = await send_custom_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, e, message, GRILLE_SS_COMPOSANTES)
            await log_chat(user_id, session_id, user_input, answer, intent, confidence)

    return list_img_str