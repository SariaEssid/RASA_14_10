"""
actions/utils/slots_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet, ActiveLoop
from actions.constants.Constants import ALL_SLOTS
from actions.logging.logging_helpers import log_info_text

import logging

log = logging.getLogger("rasa-actions")

def get_return_slots_candidat_id_fullname(id_candidat, full_name):
    try:
        slots_to_set = {
            "id_candidat": id_candidat,
            "full_name": full_name
        }

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]

    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_authentication(user_roles, id_candidat, full_name):
    try:
        slots_to_set = {
            "roles": user_roles,
            "id_candidat": id_candidat,
            "full_name": full_name
        }

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]
    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_user_fullname_roles(full_name, user_roles):
    try:
        slots_to_set = {
            "full_name": full_name,
            "roles": user_roles
        }

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]
    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_qa_intent_flow_results(user_input, answer, sscomp, intent, active_flow, last_second_question, maintained_intent, decision_mode):
    try:
        slots_to_set = {
            "last_last_question": last_second_question,
            "last_question": user_input,
            "sscomp": sscomp,
            "last_answer": answer,
            "predicted_intent": intent,
            "active_flow": active_flow,
            "last_intent": maintained_intent,
            "forward_level": decision_mode
        }

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]

    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_qa_intent_flow(user_input, answer, sscomp, intent, active_flow):
    try:
        slots_to_set = {
            "last_question": user_input,
            "sscomp": sscomp,
            "last_answer": answer,
            "predicted_intent": intent,
            "active_flow": active_flow
        }

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]

    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_qa_intent_flow_followed(user_input, sscomp, intent, decision_mode, last_intent, active_flow, last_last_question):
    try:
        slots_to_set = {
            "last_question": user_input,
            "sscomp": sscomp,
            "predicted_intent": intent,
            "forward_level": decision_mode,
            "last_intent": last_intent,
            "active_flow": active_flow,
            "last_last_question": last_last_question
        }

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]

    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_flow(active_flow):
    try:
        slots_to_set = {
            "active_flow": active_flow
        }
        ActiveLoop(None)
        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]

    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def get_return_slots_for_conversations(slots_to_set):
    try:
        ActiveLoop(None)

        for k, v in slots_to_set.items():
            log_info_text("❤️  ", f"   {k} : {v}")

        return [SlotSet(k, v) for k, v in slots_to_set.items() if k in ALL_SLOTS]

    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def clear_slots():
    try:
        return [SlotSet(slot, None) for slot in ALL_SLOTS]
    except Exception as e:
        log.error(f"🚨  Error clearing slots: {e}")
        return empty_slots()

def empty_slots() -> list:
    """Standard empty slot response for Rasa actions."""
    return []

def get_conversational_slots(tracker: Tracker):
    # 1️⃣ Get all user messages from tracker events
    all_messages = [
        e.get("text")
        for e in tracker.events
        if e.get("event") == "user" and e.get("text")
    ]

    # 2️⃣ Identify last and second-to-last questions
    # last_first_question = all_messages[-1] if len(all_messages) >= 1 else None # Equivalent to question = tracker.latest_message.get("text", "").strip()
    last_second_question = all_messages[-2] if len(all_messages) >= 2 else None

    # 3️⃣ Log for debug
    # 🦁 log_info_text("TRACK CONV - ALL USER MESSAGES: ", str(all_messages))
    log_info_text("TRACK CONV - LAST 2 QUESTION: ", last_second_question)

    # RETRIEVE ALL EVENTS + ENTITIES
    # last_events = tracker.events[-5:]
    # history = "\n".join([str(e) for e in last_events])
    # latest_entities = tracker.latest_message.get("entities")
    # log_warn_text("history: ", history)
    # log_warn_text("latest_entities: ", str(latest_entities))

    return last_second_question

def get_slot_sscomp(tracker):
    return tracker.get_slot("sscomp")

def get_slots_to_set(my_last_sscomp_value, last_second_question, question, answer, intent, decision_mode) :
    return {
        "active_flow": None,
        "sscomp": my_last_sscomp_value,
        "last_last_question": last_second_question,
        "last_question": question,
        "last_answer": answer,
        "last_intent": intent,
        "forward_level": decision_mode
    }

def get_slots_to_set_json(slot_session_value, slot_speciality_value, slot_grade_value, last_second_question, question, answer, intent, decision_mode) :

    return {
        "active_flow": None,
        "session": slot_session_value,
        "speciality": slot_speciality_value,
        "grade": slot_grade_value,
        "last_last_question": last_second_question,
        "last_question": question,
        "last_answer": answer,
        "last_intent": intent,
        "forward_level": decision_mode
    }

def get_slots_to_set_eval_pj(my_last_sscomp_value, slot_speciality_value, last_second_question, question, answer, intent, decision_mode) :

    return {
        "active_flow": None,
        "sscomp": my_last_sscomp_value,
        "speciality": slot_speciality_value,
        "last_last_question": last_second_question,
        "last_question": question,
        "last_answer": answer,
        "last_intent": intent,
        "forward_level": decision_mode
    }

def get_slots_to_set_last_answer_flow(active_flow, answer) :

    return {
        "active_flow": active_flow,
        "last_answer": answer
    }

def get_slots_to_set_maintain_conv(last_second_question, question, answer, intent, decision_mode) :

    return {
        "last_last_question": last_second_question,
        "last_question": question,
        "last_answer": answer,
        "last_intent": intent,
        "forward_level": decision_mode
    }

def get_slots_to_set_maintain_active_flow(last_second_question, question, answer, intent, decision_mode, active_flow) :

    return {
        "last_last_question": last_second_question,
        "last_question": question,
        "last_answer": answer,
        "last_intent": intent,
        "forward_level": decision_mode,
        "active_flow": active_flow
    }

def get_slots_to_set_maintain_conv_qa(last_second_question, question, intent, decision_mode) :

    return {
        "last_last_question": last_second_question,
        "last_question": question,
        "last_intent": intent,
        "forward_level": decision_mode
    }