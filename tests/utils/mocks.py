"""
Enterprise-grade mocks for Rasa + HTTP + dispatcher
"""
from unittest.mock import MagicMock

from aiocircuitbreaker import CircuitBreaker, CircuitBreakerError

from tests.unit.test_action_context_flow import Tracker

class MockDispatcher:
    def __init__(self):
        self.messages = []

    def utter_message(self, text=None, **kwargs):
        self.messages.append({
            "text": text,
            "kwargs": kwargs
        })


class MockTracker:
    def __init__(self,
                 sender_id="user-1",
                 intent="test",
                 confidence=0.9,
                 slots=None):

        self.sender_id = sender_id
        self.latest_message = {
            "text": "hello",
            "intent": {
                "name": intent,
                "confidence": confidence
            }
        }
        self._slots = slots or {}

    def get_slot(self, key):
        return self._slots.get(key, "mock-slot")


class MockHttpResponse:
    def __init__(self, status_code=200, text="OK"):
        self.status_code = status_code
        self.text = text
        self.is_success = status_code < 400


class MockHttpClient:
    @staticmethod
    async def get(_self, *_args, **_kwargs):
        return MockHttpResponse()

class DummyResponse:
    def __init__(self, status_code=200, text="OK", is_success=True):
        self.status_code = status_code
        self.text = text
        self.is_success = is_success


class DummyFailResponse:
    def __init__(self):
        self.status_code = 500
        self.text = "FAIL"
        self.is_success = False

def create_fake_tracker(slots=None):
    tracker = MagicMock(spec=Tracker)
    tracker.slots = slots or {}
    # Implémentation flexible de get_slot
    tracker.get_slot.side_effect = lambda key: tracker.slots.get(key)
    return tracker

def create_fake_tracker_off(slots=None):
    # Retirez 'spec=Tracker' pour éviter la limitation stricte
    tracker = MagicMock()
    tracker.slots = slots or {}
    # L'assignation du side_effect fonctionnera maintenant car le mock
    # acceptera la création de l'attribut get_slot
    tracker.get_slot.side_effect = lambda key: tracker.slots.get(key)
    return tracker

side_effect=CircuitBreakerError(MagicMock(spec=CircuitBreaker), "Circuit Open")