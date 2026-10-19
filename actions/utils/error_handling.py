"""
actions/utils/error_handling.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from functools import wraps
from typing import Callable, Any, Text, Dict, List
from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from datetime import datetime, timezone
from actions.constants.Constants import BOT_MESSAGES
from actions.utils.message_helpers import send_fallback_problem_to_dsi_forwarded_by_buttons

import logging
import httpx

logger = logging.getLogger(__name__)

# In error_handling.py - enhance the decorator
def handle_action_errors(original_func: Callable) -> Callable:
    @wraps(original_func)
    async def wrapper(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            return await original_func(self, dispatcher, tracker, domain)
        except httpx.HTTPStatusError as e:
            # Specific handling for HTTP errors
            if e.response.status_code == 401:
                dispatcher.utter_message(BOT_MESSAGES.get('failed_auth'))
            elif e.response.status_code == 404:
                dispatcher.utter_message(BOT_MESSAGES.get('result_not_found'))
            else:
                dispatcher.utter_message(BOT_MESSAGES.get('official_tech_problem'))
            logger.error(f"HTTP error in : {e.response.status_code} - {e.response.text}")

        except Exception as e:
            # Existing general error handling
            logger.error(f"Error in : {str(e)}", exc_info=True)
            payload_tech_error = {
                "userId": tracker.sender_id,
                "sessionId": tracker.get_slot("session_id"),
                "userInput": tracker.latest_message.get("text"),
                "rasaIntent": tracker.latest_message.get("intent", {}).get("name"),
                "confidence": tracker.latest_message.get("intent", {}).get("confidence"),
                "messageExchangeDate": datetime.now(timezone.utc).isoformat()
            }
            await send_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, "CENTRAL_HANDLING_ERROR", payload_tech_error, e)

        return [SlotSet("password", None)]
    return wrapper