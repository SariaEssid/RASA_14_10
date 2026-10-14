"""
actions/util_actions/common_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.constants.ActionsNome import ActionsNome
from actions.logging.logging_helpers import log_info_text

def get_slot_safe(tracker, name):
    for e in reversed(tracker.events):
        if e.get("event") == "slot" and e.get("name") == name:
            return e.get("value")
    return tracker.get_slot(name)

class ActionUtterBotTyping(Action):
    def name(self) -> Text:
        # Per your preference, ensure this aligns with your
        # TRAINING_EXAMPLES_id_training_example_seq logic if used in training data
        return ActionsNome.ACTION_BOT_TYPING.value

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # 1. Sending the placeholder text
        dispatcher.utter_message(text="Pensé en cours ...⏳")

        last_last_q = get_slot_safe(tracker, "last_last_question")
        last_q = get_slot_safe(tracker, "last_question")
        last_re = get_slot_safe(tracker, "last_answer")

        log_info_text("🔁 🔁 BOT_TYPING (*****) - last_last_qe: ", last_last_q)
        log_info_text("🔁 🔁 BOT_TYPING (*****) - last_qe: ", last_q)
        log_info_text("🔁 🔁 BOT_TYPING (*****) - last_re: ", last_re)

        #################################################################################"
        # Récupère l'état instantané
        slots = tracker.current_slot_values()

        last_last_qe = slots.get("last_last_question")
        last_qe = slots.get("last_question")
        last_re = slots.get("last_answer")

        log_info_text("🔁 BOT_TYPING (INSTANT) - last_last_qe: ", last_last_qe)
        log_info_text("🔁 BOT_TYPING (INSTANT) - last_qe: ", last_qe)
        log_info_text("🔁 BOT_TYPING - last_re: ", last_re)

        # 2. Extracting slot for logging/logic

        last_last_qe = tracker.get_slot("last_last_question")
        last_qe = tracker.get_slot("last_question")
        last_re = tracker.get_slot("last_answer")

        log_info_text("🔁 🔁 🔁 🔁 🔁  LOL123 - last_last_qe: ", last_last_qe)
        log_info_text("🔁 🔁 🔁 🔁 🔁  LOL123 - last_qe: ", last_qe)
        log_info_text("🔁 🔁 🔁 🔁 🔁  LOL123 - last_re: ", last_re)

        # 3. Returning the slot set (keeping it consistent)
        return []