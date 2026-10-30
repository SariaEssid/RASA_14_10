"""
actions/answer_from_file/follow_up/retrieve_decision_mode.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import re
from typing import List, cast

from actions.actions import normalize_text, check_is_excluded, remove_excluded_patterns, START_WORDS
from actions.answer_from_file.bot_missions import check_is_dead_end_prompt
from actions.answer_from_file.follow_up.detect_rooting import FollowUpDetector
from actions.answer_from_file.follow_up.pron_det_checking import check_pronoun_det
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import DIRECT_HAND_FLAG, BLOCKAGE_PATTERNS
from actions.logging.logging_helpers import log_info_text
from actions.semantic.semantic_actions import is_followup


class RAGServiceUnavailable(Exception):
    pass

##################################################
async def get_decision_mode(self, dispatcher, tracker, action_label, native_question, last_second_question, intent, last_intent) :

    last_user_response = tracker.get_slot("last_answer")
    detector = FollowUpDetector()
    signals = signal_extract(native_question, last_second_question)
    similarity = compute_similarity(native_question, last_second_question)

    is_pron_det = check_pronoun_det(native_question)

    is_dead_end = None
    is_blocked_pattern = check_is_blocked_pattern(native_question)
    if is_blocked_pattern:
        log_info_text("last_user_response : ",last_user_response)
        log_info_text("B L O C K E D   P A T T E R N : ", str(is_blocked_pattern))
        is_dead_end = await check_is_dead_end(self, dispatcher, action_label, last_second_question, last_user_response, native_question)
        log_info_text("RESULT : ", str(is_dead_end))

    is_more_det = check_more_details(native_question)

    log_info_text("is_pron_det : ", str(is_pron_det))
    decision = detector.compute_score(
        similarity=similarity,
        is_started_with_kw=signals["is_started_with_kw"],
        intent=intent,
        last_intent=last_intent,
        pron_det=is_pron_det,
        is_dead_end=is_dead_end,
        is_more_det = is_more_det,
        muted_intents=cast(List[str], ActiveIntents.MUTED_INTENTS)
    )

    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label} - ROUTING SCORE: {decision.score}")
    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label} - ROUTING MODE: {decision.mode}")
    log_info_text(f"{DIRECT_HAND_FLAG}", f"{action_label} - ROUTING REASONS: {decision.reasons}")

    return decision

async def check_is_dead_end(self, dispatcher, action_label, last_question, last_response, current_question):

    prompt = check_is_dead_end_prompt(last_question, last_response, current_question)

    log_info_text("DEAD END - 1 : ", prompt)
    answer = await self.call_llm_safe(
        dispatcher=dispatcher,
        prompt=prompt,
        action_label=action_label,
        payload_tech_error=None
    )
    log_info_text("🎯 DEAD END - 2 : ", answer)

    return answer

def check_is_blocked_pattern(current_question: str) -> bool:
    return any(re.search(pattern, current_question, re.IGNORECASE) for pattern in BLOCKAGE_PATTERNS)

def is_started_with_keyword(question: str) -> bool:
    if not question:
        return False

    cleaned_question = question.strip().lower()

    return cleaned_question.startswith(START_WORDS)

def check_more_details(current_question: str) -> bool:
    # Matches 'detail', 'détail', 'details', 'détails', 'detailler', 'détailler', 'detaille', etc.
    pattern = r"\bd[eé]tail"
    return bool(re.search(pattern, current_question, re.IGNORECASE))

def compute_similarity(current_q: str, last_q: str) -> float:
    # Guard clause: if inputs are missing, return 0.0 immediately
    if not current_q or not last_q:
        return 0.0

    try:
        return is_followup(current_q, last_q)
    except (ValueError, TypeError, AttributeError) as e:
        # Catch specific errors related to string processing or math
        log_info_text("EXCEPTION : ", str(e))
        return 0.0

def signal_extract(question: str, last_question: str):

    is_excluded, is_started_with_kw, no_muted = exist_pronoun(last_question, question)

    return {
        "is_started_with_kw": bool(is_started_with_kw),
        "is_excluded": bool(is_excluded),
        "no_muted": no_muted
    }

def exist_pronoun(last_second_question, question):
    muted_words = ["greet", "bye"]

    log_info_text("PLAN-1 : ", str(normalize_text(question)) + " - " + str(len(question.split())))

    is_excluded = None
    if check_is_excluded(question):
        is_excluded = True
        # is_pron_in_qe = False   1. donner la mission pour efm | 2. est ce que cet enseignant peut postuler pour un autre grade

    no_muted_words_found = last_second_question is not None and all(
        word.lower() not in last_second_question.lower()
        for word in muted_words
    )

    qe_without_excluded = remove_excluded_patterns(question)
    log_info_text("PLAN-3 : ", qe_without_excluded)
    is_started_with_kw = is_started_with_keyword(normalize_text(qe_without_excluded))

    log_info_text("PLAN-1 is_pron_in_qe : ", str(is_started_with_kw))

    return is_excluded, is_started_with_kw, no_muted_words_found