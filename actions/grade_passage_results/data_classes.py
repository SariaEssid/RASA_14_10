"""
actions/answer_from_file/data_classes.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class FlowCheckContext:
    dispatcher: Any
    tracker: Any
    action_label: str
    last_intent: str | None
    intent: str | None
    active_flow: str | None
    user_id: str | None
    session_id: str | None
    user_input: str
    confidence: float | None

@dataclass(frozen=True)
class GetResponseContext:
    dispatcher: Any
    tracker: Any
    action_label: str
    last_intent: str | None
    active_flow: str | None
    payload_tech_error: Any

@dataclass(frozen=True)
class ActionContext:
    user_id: str | None
    dispatcher: Any
    session_id: str | None
    active_flow: str | None
    action_label: str
    tracker: Any
    user_input: str
    answer: str | None
    intent: str | None
    confidence: float | None

@dataclass(frozen=True)
class DynamicToChainContext:
    tracker: Any
    user_input: str
    answer: str | None
    intent: str | None
    active_flow: str | None
    last_second_question: str | None
    maintained_intent: str | None
    decision_mode: str | None