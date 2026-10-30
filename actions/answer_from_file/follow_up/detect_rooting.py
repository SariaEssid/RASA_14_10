"""
actions/answer_from_file/follow_up/detect_rooting.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import re
from typing import List

import spacy

from actions.actions import normalize_text
from actions.answer_from_file.data_classes import RoutingDecision
from actions.constants.ActiveIntents import ActiveIntents
from actions.constants.Constants import DIRECT_HAND_FLAG
from actions.logging.logging_helpers import log_info_text
from actions.settings.settings import settings

nlp = spacy.load("fr_core_news_sm")

# 1. Mots qui provoquent une dépendance ABSOLUE à l'historique (Possessifs / Démonstratifs)
STRICT_DEPENDENT_WORDS = {"son", "ses", "sa", "leur", "leurs", "ce", "cet", "cette", "ces"}

# 2. Pronoms personnels, démonstratifs neutres et indéfinis contextuels
PRON_TARGETS = {"il", "elle", "ils", "elles", "ca", "ça", "cela", "chacun", "chacune"}

# Pronoms objets complémentaires
CLITIC_PRONOUNS = {"le", "la", "les"}

# Pronoms sujets ou particules de négation qui précèdent obligatoirement un pronom objet
SUBJECT_OR_NEGATION = {"je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "ne", "n'"}

MAIN_PARAM_VALUE = settings.MAIN_PARAM_VALUE

class FollowUpDetector:

    def __init__(self):
        self.threshold = settings.FOLLOWUP_THRESHOLD

    def compute_score(
        self,
        similarity: float,
        is_started_with_kw: bool,
        intent: str,
        last_intent: str,
        pron_det: int,
        is_dead_end: bool,
        is_more_det: bool,
        muted_intents: List[str]
    ) -> RoutingDecision:

        score = 0.0
        reasons = {}

        # 1. Semantic similarity
        if similarity > settings.BASIC_THRESHOLD_VALUE:
            score += self.threshold
            reasons["semantic"] = self.threshold
        else:
            reasons["semantic"] = 0.0

        log_info_text("is_dead_end : ", str(is_dead_end))
        if "True" in str(is_dead_end):
            score += MAIN_PARAM_VALUE
            reasons["dead_end"] = MAIN_PARAM_VALUE
        else:
            reasons["dead_end"] = 0.0

        if is_more_det:
            score += MAIN_PARAM_VALUE
            reasons["more_det"] = MAIN_PARAM_VALUE
        else:
            reasons["more_det"] = 0.0

        log_info_text("pron_det : ", str(pron_det))
        if pron_det > 0:
            score += MAIN_PARAM_VALUE
            reasons["pron_det"] = MAIN_PARAM_VALUE # est ce que le type de cette epreuve est pdf ou video
        else:
            reasons["pron_det"] = 0.0

        # 2. Pronoun (VERY strong)
        if is_started_with_kw:
            score += settings.MAIN_BEGIN_KEYWORD
            reasons["begin_kw"] = settings.MAIN_BEGIN_KEYWORD
        else:
            reasons["begin_kw"] = 0.0

        # 4. Intent continuity (fallback signal)
        if intent == "nlu_fallback" and last_intent not in muted_intents:
            score += settings.FALLBACK_VALUE
            reasons["fallback"] = settings.FALLBACK_VALUE
        else:
            reasons["fallback"] = 0.0

        if last_intent and last_intent in ActiveIntents.NO_FOLLOW_UP_INTENTS:
            log_info_text(f"{DIRECT_HAND_FLAG} --------------------------> MAKE SCORE=0 FROM GREET-BYE-AFFIRM-DENY => ", f" -{str(last_intent)}- IN {str(ActiveIntents.NO_FOLLOW_UP_INTENTS)}")
            score = 0.0

        log_info_text("FINAL SCORE 1 => ", f" {str(score)}")
        mode = "detailed" if score > self.threshold else "short"
        log_info_text("FINAL SCORE 2 => ", f" {str(score)} - {str(mode)}")

        return RoutingDecision(mode=mode, score=score, reasons=reasons)