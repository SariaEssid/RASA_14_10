"""
actions/semantic/semantic_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import re
from typing import Text, Dict, Any, Union, Coroutine

import numpy as np
from rasa_sdk import Tracker
from rasa_sdk.events import FollowupAction
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import normalize_text, is_followup, track_prompt_decision_params
from actions.answer_from_file.answer_from_file_actions import BaseDynamicLLMAction
from actions.answer_from_file.follow_up.retrieve_decision_mode import get_decision_mode
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.ActionsNome import ActionsNome
from actions.constants.Constants import BOT_MESSAGES, FEEDBACK_BUTTONS, DIRECT_HAND_FLAG
from actions.context_awareness_flow.action_context_awareness import get_forwarded_action
from actions.logging.logger import log_faiss_unknown_question, log_chat
from actions.logging.logging_helpers import get_current_intent, log_info_text, get_util_values_for_semantic, \
    log_exception_text, log_error_text, get_util_values_with_log
from actions.semantic.semantic import get_index, get_answers, get_model
from actions.settings.settings import settings
from actions.utils.error_handling import handle_action_errors
from actions.utils.message_helpers import send_multiple_messages_forwarded_by_buttons, exit_for_empty_and_long_question
from actions.utils.slots_helpers import get_return_slots_qa_intent_flow, get_slot_sscomp, \
    get_return_slots_qa_intent_flow_followed


class ActionSemanticQA(BaseDynamicLLMAction):
    def __init__(self, semantic_qa_service: Any = None):
        super().__init__()
        self.semantic_qa_service = semantic_qa_service

    def name(self) -> Text:
        return ActionsNome.ACTION_SEMANTIC_QA.value

    @handle_action_errors
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Union[list[Any], Coroutine[Any, Any, list[Any]]]:

        action_label = ActionsLabel.PY_SEMANTIC.value

        detected_question = tracker.latest_message.get("text").strip()
        predicted_intent = tracker.latest_message.get("intent", {}).get("name")

        log_info_text("OLD : ", detected_question)
        question = normalize_text(detected_question)
        log_info_text("NEW : ", question)

        if exit_for_empty_and_long_question(dispatcher, question):
            return []

        if not is_valid_question(dispatcher, question):
            return []

        last_intent, intent, active_flow, last_user_question, last_user_response = get_semantic_values(tracker)
        decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, question, last_user_question, intent, last_intent)
        track_prompt_decision_params(action_label, "prompt", decision_infos)

        decision_mode = decision_infos.mode
        if decision_mode == "detailed":
            get_util_values_with_log(tracker, action_label)
            answer = await follow_up_semantic(self, dispatcher, tracker, question, predicted_intent, domain)
            return answer

        intent = get_current_intent(tracker)
        log_info_text(action_label, action_label + " - " + intent)

        fallback_answer = BOT_MESSAGES.get("fallback_message")

        # --- Load resources safely ---
        try:
            faiss_index = get_index()
            answers = get_answers()
            model = get_model()
        except Exception as e:
            log_exception_text(action_label, f"Semantic resources not ready: {e}")
            send_multiple_messages_forwarded_by_buttons(dispatcher, BOT_MESSAGES.get('no_context_found'), FEEDBACK_BUTTONS)
            return flatten_events(
                get_return_slots_qa_intent_flow(
                    question,
                    fallback_answer,
                    get_slot_sscomp(tracker),
                    None,
                    None
                )
            )

        # --- User message ---

        if not question:
            send_multiple_messages_forwarded_by_buttons(dispatcher, fallback_answer, FEEDBACK_BUTTONS)
            return flatten_events(
                get_return_slots_qa_intent_flow(
                    question,
                    fallback_answer,
                    get_slot_sscomp(tracker),
                    None,
                    None
                )
            )
        # --- Encode for FAISS ---
        try:
            question_embedding = encode_for_faiss(model, question)
        except Exception as e:
            log_exception_text(action_label, f"Failed to encode message: {e}")
            send_multiple_messages_forwarded_by_buttons(dispatcher, fallback_answer, FEEDBACK_BUTTONS)
            return flatten_events(
                get_return_slots_qa_intent_flow(
                    question,
                    fallback_answer,
                    get_slot_sscomp(tracker),
                    None,
                    None
                )
            )
        # --- FAISS search ---
        try:
            D, I = safe_faiss_search(faiss_index, question_embedding, k=1)
            score = D[0][0]
            best_index = int(I[0][0])
        except Exception as e:
            log_exception_text(action_label, f"FAISS search failed: {e}")
            send_multiple_messages_forwarded_by_buttons(dispatcher, fallback_answer, FEEDBACK_BUTTONS)
            return flatten_events(
                get_return_slots_qa_intent_flow(
                    question,
                    fallback_answer,
                    get_slot_sscomp(tracker),
                    None,
                    None
                )
            )

        # --- Context info ---

        session_id = tracker.get_slot("session_id")
        active_flow = tracker.get_slot("active_flow")
        user_id = tracker.sender_id

        # --- Log semantic info ---
        last_user_question, last_user_answer = get_util_values_for_semantic(tracker, action_label, question, score, best_index, active_flow, user_id, predicted_intent)
        log_info_text(action_label, "ℹ️ ℹ️ ℹ️ ℹ️ ℹ️ " + last_user_question)

        # --- Select answer ---
        try:
            sscomp = tracker.get_slot("sscomp")
            log_info_text(action_label, f"sscomp: {sscomp}")
            if not sscomp and score > settings.SEMANTIC_THRESHOLD:
                active_flow = tracker.get_slot("active_flow")
                if isinstance(answers, list):
                    best_answer = answers[best_index]
                elif isinstance(answers, dict):
                    best_answer = list(answers.values())[best_index]
                else:
                    raise TypeError("Answers must be list or dict")
                answer = best_answer.replace("\\n", "\n")
                send_multiple_messages_forwarded_by_buttons(dispatcher, answer, FEEDBACK_BUTTONS)
                await log_chat(user_id, session_id, question, answer, intent, 1)
                return flatten_events(
                    get_return_slots_qa_intent_flow(
                        question,
                        answer,
                        get_slot_sscomp(tracker),
                        None,
                        active_flow
                    )
                )
            else:
                await log_faiss_unknown_question(question, score, best_index, predicted_intent, user_id, session_id)
                reponse = await follow_up_semantic(self, dispatcher, tracker, question, predicted_intent, domain)
                return reponse

        except Exception as e:
            log_exception_text(action_label, f"Answer retrieval error: {e}")
            await log_chat(user_id, session_id, question, str(e), intent, 1)
            return flatten_events(
                get_return_slots_qa_intent_flow(
                    question,
                    fallback_answer,
                    get_slot_sscomp(tracker),
                    None,
                    None
                )
            )

async def follow_up_semantic(self, dispatcher, tracker, question, predicted_intent, domain):

    last_intent, intent, active_flow, last_user_question, last_user_response = get_semantic_values(tracker)

    action_label = ActionsLabel.PY_SEMANTIC.value
    followup = is_followup(question, last_user_question)
    # Detect follow-up option based on keywords

    decision_infos = await get_decision_mode(self, dispatcher, tracker, action_label, question, last_user_question, intent, last_intent)
    decision_mode = decision_infos.mode

    track_prompt_decision_params(action_label, "prompt", decision_infos)

    log_info_text(action_label, f"{DIRECT_HAND_FLAG} R O L L B A C K   D E C I S I O N : ")
    log_info_text(action_label, "Current Question : " + question)
    log_info_text(action_label, "Last Question : " + last_user_question)
    log_info_text(action_label, "Last Response : " + last_user_response)
    log_info_text(action_label, "FOLLOW by semantic : " + str(followup))
    log_info_text(action_label, "Decision mode : " + decision_mode)


    last_intent, action = get_forwarded_action(tracker, action_label, followup, decision_mode)

    # Retrieve the list of SlotSet events
    events = get_return_slots_qa_intent_flow_followed(
        last_user_question,
        get_slot_sscomp(tracker),
        predicted_intent,
        decision_mode,
        last_intent,
        active_flow,
        last_user_question
    )

    if action and action in domain.get("actions", []):
        events.append(FollowupAction(action))
    else:
        log_error_text(action_label, f"Invalid forwarded action: {action}")

    # Append the FollowupAction to the FLAT list
    events = flatten_events(events)
    return events

def encode_for_faiss(model, text: str) -> np.ndarray:
    """Encode text for FAISS search: 2D float32 embedding"""
    emb = np.array(model.encode([text], normalize_embeddings=True), dtype=np.float32)
    if emb.ndim == 1:
        emb = emb.reshape(1, -1)
    return emb

def safe_faiss_search(index, embedding, k=1):
    """Perform FAISS search safely, handling empty or None index"""
    if index is None or index.ntotal == 0:
        raise RuntimeError("FAISS index not loaded or empty")

    k = min(k, index.ntotal)
    embedding = np.array(embedding, dtype=np.float32)
    if embedding.ndim == 1:
        embedding = embedding.reshape(1, -1)

    D, I = index.search(embedding, k)
    return D, I

def flatten_events(events):
    flat = []
    for e in events:
        if isinstance(e, list):
            flat.extend(e)
        else:
            flat.append(e)
    return flat

def is_valid_question(dispatcher, text) -> bool:
    """
    Returns True if the text looks like a legitimate question/sentence,
    and False if it contains excessive noise, gibberish, or mashed keys.
    """
    if not text or not text.strip():
        return False

    text = text.strip()

    # 1. Clean out common punctuation that doesn't count as noise
    # (keeps letters, numbers, spaces, and normal punctuation like ?, !, ., ', -)
    clean_text = re.sub(r"[?!.,'\-\s]", "", text)

    # 2. Extract remaining bad symbols (+, *, =, _, /, etc.)
    special_chars = re.findall(r"[^\w\s]", clean_text)

    # 3. Calculate noise ratio
    # If more than 20% of the non-space characters are weird symbols, it's noise.
    if len(clean_text) > 0:
        noise_ratio = len(special_chars) / len(clean_text)
        if noise_ratio > 0.20:
            dispatcher.utter_message(BOT_MESSAGES.get('typo_in_qe'))
            return False

    # 4. Check for meaningless repetitive patterns (e.g., -+-.-0-00-00)
    if re.search(r"([-+.*0_]{4,})", text):
        dispatcher.utter_message(BOT_MESSAGES.get('typo_in_qe'))
        return False

    # 5. Word lengths check (optional, flags typing blindly like 'asdfghjkl')
    # If the user typed something, but there are no actual letters anywhere
    if not any(c.isalpha() for c in text):
        dispatcher.utter_message(BOT_MESSAGES.get('typo_in_qe'))
        return False

    return True

def get_semantic_values(tracker):

    last_intent = tracker.get_slot("last_intent")
    intent = tracker.get_slot("intent")
    active_flow = tracker.get_slot("active_flow")
    last_user_question = tracker.get_slot("last_question")
    last_user_response = tracker.get_slot("last_answer")

    return last_intent, intent, active_flow, last_user_question, last_user_response