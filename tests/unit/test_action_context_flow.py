"""
tests/unit/test_action_context_flow.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.utils.slots_helpers import get_conversational_slots

class Tracker:
    events = [
        {"event": "user", "text": "hello"},
        {"event": "user", "text": "world"}
    ]

def test_conversation():
    t = Tracker()
    res = get_conversational_slots(t)
    assert res == "hello"