"""
tests/unit/test_message_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.utils.message_helpers import (
    send_multiple_messages_forwarded_by_buttons,
    send_multiple_messages_images_forwarded_by_buttons,
    adjust_lines,
    get_random_message
)

class DummyDispatcher:
    def __init__(self):
        self.calls = []

    def utter_message(self, **kwargs):
        self.calls.append(kwargs)

def test_adjust_lines():
    assert adjust_lines("a\\nb") == "a\nb"

def test_send_multiple_messages_forwarded_by_buttons():
    d = DummyDispatcher()
    send_multiple_messages_forwarded_by_buttons(d, "hello", [{"title": "btn"}])
    assert len(d.calls) > 0

def test_send_images():
    d = DummyDispatcher()
    send_multiple_messages_images_forwarded_by_buttons(
        d,
        "hello",
        ["base64img"],
        [{"title": "btn"}],
        "more"
    )
    assert d.calls

def test_get_random_message():
    msg = get_random_message(["a", "b", "c"])
    assert msg in ["a", "b", "c"]