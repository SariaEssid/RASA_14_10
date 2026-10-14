"""
tests/unit/test_action_semantic_qa.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.actions import get_semantic_random_reply

def test_no_candidates():
    r = get_semantic_random_reply([], "label", "hello")
    assert isinstance(r, str)