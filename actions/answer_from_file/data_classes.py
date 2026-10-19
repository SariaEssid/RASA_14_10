"""
actions/answer_from_file/data_classes.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
from __future__ import annotations

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

@dataclass
class RequiredValuesShortAnswers:
    action_label: str
    intent: str | None
    last_intent: str | None
    domains: list[str]
    native_question: str
    new_nbr_chunks: int
    detected_slots: list[str]
    entities: list[str]
    is_hard: bool