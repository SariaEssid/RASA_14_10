"""
actions/answer_from_file/data_classes.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from dataclasses import dataclass
from typing import Any

@dataclass
class MyConversationContext:
    tracker: Any
    action_label: str
    last_second_question: str
    decision_mode: str
    intent: str
    last_intent: str
    question: str
    json_text: str

@dataclass
class MyConversationContextSlots:
    tracker: Any
    nbr_chunks: int
    action_label: str
    native_question: str
    entities: list[str]
    detected_slots: list[str]

@dataclass
class RoutingDecision:
    mode: str            # "short" | "detailed"
    score: float
    reasons: dict