"""
actions/authentication/auth_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from abc import abstractmethod, ABC
from typing import Text, Dict, Any, List
from typing import TypeVar, Generic, Tuple, TypedDict
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from actions.authentication.credentials import validate_credentials, fallback_credentials, is_flow, send_invalid_format
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import BOT_MESSAGES
from actions.logging.logger import log_chat
from actions.logging.logging_helpers import get_util_values_for_authentication, log_info_text, log_info_auth, \
    log_info_expected_flow, \
    log_warn_text
from actions.settings.settings import settings
from actions.utils.error_handling import handle_action_errors
from actions.utils.message_helpers import original_alert_unexpected_response, send_message_forwarded_by_buttons
from actions.utils.slots_helpers import empty_slots, get_return_slots_authentication, \
    get_return_slots_candidat_id_fullname

import time

T = TypeVar('T', bound='IResultsService')

class ValidationResult(TypedDict, total=False):
    valid: bool
    full_name: Text
    id_user: int
    jwt: Text
    roles: List[Text]
    username: Text
    password: Text

class BaseCredentialsAction(Action, Generic[T], ABC):
    """Base class handling all credential-related functionality with CIRCUIT breaker"""

    def __init__(self, service: T):
        self.service = service
        self.common_slots: List[SlotSet] = []
        self._total_requests = 0
        self._failed_requests = 0

        # 🌟 ADD: Store failure data with timestamps
        self._auth_failures = 0
        self._format_failures = 0
        self._flow_failures = 0
        self._auth_failure_data: Dict[str, Tuple[int, float]] = {}  # {key: (failure_count, last_failure_time)}
        #####🌟

    @abstractmethod
    def name(self) -> Text:
        pass

    @abstractmethod
    def expected_flow(self) -> Text:
        pass

    @abstractmethod
    async def execute_service_logic(
            self, validation: ValidationResult, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        pass

    # 🌟 ENHANCE: Better metrics with failure breakdown
    def _get_action_metrics(self) -> Dict[str, Any]:
        """Collect metrics for monitoring"""
        total = max(self._total_requests, 1)
        success_rate = ((total - self._failed_requests) / total) * 100

        return {
            "action_name": self.name(),
            "total_requests": self._total_requests,
            "failed_requests": self._failed_requests,
            "auth_failures": self._auth_failures,
            "format_failures": self._format_failures,
            "flow_failures": self._flow_failures,
            "success_rate": f"{success_rate:.1f}%",
            "current_flow": self.expected_flow()
        }
    #🌟

    @handle_action_errors
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        intent = tracker.latest_message.get("intent", {}).get("name")
        if intent in ActiveIntents.ALL_ENTRY_INTENTS or intent == ActiveIntents.NLU_FALLBACK.value:
            log_info_text("AUTH", BOT_MESSAGES.get('skip_unrelated_action'))
            return empty_slots()

        # ✅ Increment request counter
        self._total_requests += 1

        last_intent = tracker.get_slot("last_intent")

        text = tracker.latest_message.get('text', '')
        # log.info.text("AZERTY-0 : ", tracker.get_slot("active_flow"))
        username, password = fallback_credentials(tracker, text)

        action_label = ActionsLabel.PY_BASE_CREDENTIALS.value
        session_id = get_util_values_for_authentication(tracker, action_label)
        waiting_time = settings.TOTAL_WAIT_SECONDS / 60
        log_info_expected_flow(action_label, self.expected_flow())

        # 🌟 ADD: Check for repeated authentication failures
        if self._is_excessive_auth_failures(action_label, session_id, username, waiting_time):
            dispatcher.utter_message(f"{BOT_MESSAGES.get('many_attempts')} {settings.TOTAL_WAIT_SECONDS / 60:.0f} minutes.")
            self._failed_requests += 1
            self._auth_failures += 1
            return empty_slots()
        #🌟

        # 1. Check flow validity
        if not is_flow(tracker, self.expected_flow()):
            msg = original_alert_unexpected_response()
            send_message_forwarded_by_buttons(dispatcher, msg)
            self._failed_requests += 1
            self._flow_failures += 1 #🌟

            await log_chat(
                tracker.sender_id,
                tracker.get_slot("session_id"),
                tracker.latest_message.get("text"),
                msg,
                tracker.get_intent_of_latest_message(),
                tracker.latest_message.get("intent", {}).get("confidence")
            )
            return empty_slots()

        log_info_text(action_label, f"last_intent : {last_intent}")

        if last_intent in ActiveIntents.RESULTS_INTENTS or last_intent == ActiveIntents.HOW_AUTHENTICATE_WITH_CHATBOT.value or last_intent == ActiveIntents.NLU_FALLBACK.value:
            # 2. Check if credentials are missing
            log_info_text("AZERTY-00 : " , tracker.get_slot("active_flow"))
            if not username or not password:
                if not username:
                    dispatcher.utter_message(text=BOT_MESSAGES.get('prompt_input_username'))
                if not password:
                    dispatcher.utter_message(text=BOT_MESSAGES.get('prompt_input_access_id'))
                self._failed_requests += 1
                self._flow_failures += 1  #🌟
                return empty_slots()

            # 3. Check format FIRST (before any authentication attempt)
            if await send_invalid_format(dispatcher, tracker, username, password):
                self._failed_requests += 1
                self._format_failures += 1  #🌟

                return empty_slots()

            # 4. Validate credentials if format is correct
            validation = await validate_credentials(dispatcher, tracker, username, password, self.service.verif_credentials, action_label)
            log_info_text(action_label, f"BASE-JWT+Roles : {validation}")

            if not validation.get("valid"):
                self._failed_requests += 1
                self._auth_failures += 1  #🌟

                # 🌟 ADD: Track this specific authentication failure
                self._track_auth_failure(session_id, username)  #🌟

                return empty_slots()

            # 🌟 ADD: Reset auth failures on successful login
            self._reset_auth_failures(session_id, username)  #🌟

            # ✅ Logging extracted values
            user_jwt = validation.get("jwt")
            user_roles = validation.get("roles", [])
            if user_jwt and user_roles:
                log_info_auth(action_label, user_roles, user_jwt)

            # 5. Execute service logic if credentials are valid
            results = await self.execute_service_logic(validation, dispatcher, tracker, domain)

            # 🌟 ADD metrix
            #metrics = self._get_action_metrics()
            #log.info(f"Base Action Metrics - {metrics}") #🌟

            # Always store sensitive data in slots, not class variables
            return results + get_return_slots_authentication(
                user_jwt, user_roles, validation.get("id_user"), validation.get("full_name")
            )
        else:
            return []

    # ✅ ADD: Methods to track excessive authentication failures WITH TIMESTAMPS
    def _track_auth_failure(self, session_id: str, username: str) -> None:
        """Track authentication failures for rate limiting with timestamps"""
        key = f"{session_id}_{username}"
        current_time = time.time()

        # Get current failure data or initialize
        current_failures, last_failure_time = self._auth_failure_data.get(key, (0, current_time))

        # ADD: Reset counter if last failure was more than X minutes ago
        if current_time - last_failure_time > settings.TOTAL_WAIT_SECONDS:  # X minutes in seconds
            current_failures = 1  # Reset to 1 for this new failure
        else:
            current_failures += 1

        # Update with new failure count and current timestamp
        self._auth_failure_data[key] = (current_failures, current_time)

        log_info_text("BASE_CREDENTIALS", f"Authentication failure #{current_failures} for session {session_id}, user {username} at {time.ctime(current_time)}")

    def _reset_auth_failures(self, session_id: str, username: str) -> None:
        """Reset failure counter on successful authentication"""
        key = f"{session_id}_{username}"
        if key in self._auth_failure_data:
            del self._auth_failure_data[key]
            log_info_text("AUTHENTICATION", f"Reset auth failures for session {session_id}, user {username}")

    def _is_excessive_auth_failures(self, action_label: str, session_id: str, username: str, waiting_time: float) -> bool:
        """Check if there are too many authentication failures within time window"""
        key = f"{session_id}_{username}"
        current_time = time.time()

        if key in self._auth_failure_data:
            failures, last_failure_time = self._auth_failure_data[key]
            log_info_text(action_label, f"Excessive auth failures for session {session_id}, user {username} within {waiting_time} min")
            # ✅ ADD: Check if failures are within the X-minute window
            if current_time - last_failure_time <= settings.TOTAL_WAIT_SECONDS:  # X minutes in seconds
                # Block after 5 consecutive failures within X minutes
                if failures >= settings.INVALID_CREDENTIALS_TENTATIVE_COUNT:
                    time_remaining = settings.TOTAL_WAIT_SECONDS - (current_time - last_failure_time)
                    minutes_remaining = int(time_remaining / 60)
                    log_warn_text(action_label, f"Excessive auth failures ({failures}) within {waiting_time} min for session {session_id}, user {username}. Blocked for {minutes_remaining} more minutes.")
                    return True
            else:
                # ✅ ADD: Auto-reset if last failure was more than X minutes ago
                log_info_text(action_label,f"Auto-resetting auth failures for {username} - last failure was over {waiting_time} minutes ago")
                del self._auth_failure_data[key]

        return False
