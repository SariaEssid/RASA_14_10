"""
tests/conftest.py

Enterprise-grade pytest fixtures for Rasa + services testing
@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import sys
import asyncio
from pathlib import Path

import pytest

# Make project root importable
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# =========================
# DISPATCHER MOCK (ENTERPRISE)
# =========================
class FakeDispatcher:
    """
    Simulates Rasa CollectingDispatcher with full message traceability
    """

    def __init__(self):
        self.messages = []

    def utter_message(self, text=None, *args, **kwargs):
        self.messages.append({
            "text": text,
            "args": args,
            "kwargs": kwargs
        })

    def last_message(self):
        return self.messages[-1] if self.messages else None

    def clear(self):
        self.messages.clear()


# =========================
# TRACKER MOCK (ENTERPRISE)
# =========================
class FakeTracker:
    """
    Simulates Rasa Tracker with slots + intent + message history
    """

    def __init__(
        self,
        sender_id="user-1",
        intent_name="test",
        intent_confidence=0.9,
        slots=None
    ):
        self.sender_id = sender_id

        self.latest_message = {
            "text": "hello",
            "intent": {
                "name": intent_name,
                "confidence": intent_confidence
            }
        }

        self._slots = slots or {}

        self.events = []

    def get_slot(self, key):
        return self._slots.get(key, "mock-slot")

    def set_slot(self, key, value):
        self._slots[key] = value

    def add_event(self, event):
        self.events.append(event)

    def reset(self):
        self._slots.clear()
        self.events.clear()


# =========================
# FIXTURES
# =========================
@pytest.fixture
def dispatcher():
    return FakeDispatcher()


@pytest.fixture
def _tracker():
    return FakeTracker()

@pytest.fixture(scope="session", autouse=True)
def fix_event_loop():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()