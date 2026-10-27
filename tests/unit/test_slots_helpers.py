# noinspection PyPackageRequirements
"""
@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from unittest.mock import MagicMock, patch

import pytest
from rasa_sdk import Tracker

from actions.utils.slots_helpers import (
    get_return_slots_candidat_id_fullname,
    get_return_slots_qa_intent_flow_results,
    get_return_slots_qa_intent_flow,
    get_return_slots_qa_intent_flow_followed,
    get_return_slots_flow,
    get_return_slots_for_conversations,
    clear_slots,
    empty_slots,
    get_conversational_slots,
    get_slot_sscomp,
    get_slots_to_set,
    get_slots_to_set_json,
    get_slots_to_set_eval_pj,
    get_slots_to_set_last_answer_flow,
    get_slots_to_set_maintain_conv,
    get_slots_to_set_maintain_active_flow,
    get_slots_to_set_maintain_conv_qa
)

PATCH_TARGET = "actions.utils.slots_helpers"


# ==============================================================================
# FIXTURES & INITIAL STATE SETUP
# ==============================================================================

@pytest.fixture(autouse=True)
def mock_all_slots():
    """Mock ALL_SLOTS to control exactly which parameters pass filtering."""
    allowed_slots = [
        "id_candidat", "full_name", "roles", "last_last_question",
        "last_question", "sscomp", "last_answer", "predicted_intent",
        "active_flow", "last_intent", "forward_level", "session", "speciality", "grade"
    ]
    with patch(f"{PATCH_TARGET}.ALL_SLOTS", allowed_slots):
        yield allowed_slots


@pytest.fixture
def mock_tracker() -> MagicMock:
    tracker = MagicMock(spec=Tracker)
    tracker.events = []
    tracker.get_slot = MagicMock(return_value="architecture_software")
    return tracker


# ==============================================================================
# 1. RASA SLOT SETTING UTILITIES (RETURN EVENTS LISTS)
# ==============================================================================

def test_get_return_slots_candidat_id_fullname():
    events = get_return_slots_candidat_id_fullname("candidat_123", "Saria Essid")
    assert len(events) == 2
    assert any(e.get("name") == "id_candidat" and e.get("value") == "candidat_123" for e in events)
    assert any(e.get("name") == "full_name" and e.get("value") == "Saria Essid" for e in events)

def test_get_return_slots_qa_intent_flow():
    events = get_return_slots_qa_intent_flow("Q", "A", "sscomp_val", "intent_val", "flow_val")
    assert len(events) == 5
    assert any(e.get("name") == "last_question" and e.get("value") == "Q" for e in events)
    assert any(e.get("name") == "active_flow" and e.get("value") == "flow_val" for e in events)


def test_get_return_slots_qa_intent_flow_followed():
    events = get_return_slots_qa_intent_flow_followed("Q", "comp", "intent", 2, "l_intent", "flow", "L_Q")
    assert len(events) == 7
    assert any(e.get("name") == "last_last_question" and e.get("value") == "L_Q" for e in events)
    assert any(e.get("name") == "forward_level" and e.get("value") == 2 for e in events)


def test_get_return_slots_flow():
    events = get_return_slots_flow("new_active_flow")
    assert len(events) == 1
    assert any(e.get("name") == "active_flow" and e.get("value") == "new_active_flow" for e in events)

def test_clear_slots(mock_all_slots):
    events = clear_slots()
    assert len(events) == len(mock_all_slots)
    for event in events:
        assert event.get("value") is None

def test_empty_slots():
    assert empty_slots() == []


# ==============================================================================
# 2. FILTERING BOUNDARY CONDITIONS & EXCEPTION HANDLING
# ==============================================================================

def test_slot_filtering_exclusion():
    """Verify that parameters missing from ALL_SLOTS are excluded from SlotSet generation."""
    with patch(f"{PATCH_TARGET}.ALL_SLOTS", ["id_candidat"]):
        events = get_return_slots_candidat_id_fullname("c_100", "Saria")
        assert len(events) == 1
        assert events[0].get("name") == "id_candidat"


def test_slots_helpers_generic_exception_handling():
    """Forcing a built-in parameter error to evaluate empty fallback behavior logic loop."""
    with patch(f"{PATCH_TARGET}.ALL_SLOTS", None), patch(f"{PATCH_TARGET}.log") as mock_logger:
        events = get_return_slots_flow("crash_flow")
        assert events == []
        mock_logger.error.assert_called_once()


# 🧪 TARGETED UNIT TESTS FOR 100% CODE COVERAGE (EXCEPT BLOCKS)
def test_all_except_blocks_coverage():
    """Mocks SlotSet instantiation initialization parameters to trigger exceptions across all targets."""

    def side_effect_raise(*_args, **_kwargs):
        raise ValueError("Simulated Slot Exception for Coverage")

    with patch(f"{PATCH_TARGET}.SlotSet", side_effect=side_effect_raise), \
            patch(f"{PATCH_TARGET}.log") as _mock_logger:
        # Sequentially call all helpers wrapped in try-except statements
        assert get_return_slots_candidat_id_fullname("id", "name") == []
        assert get_return_slots_qa_intent_flow_results("q", "a", "s", "i", "f", "l", "m", 1) == []
        assert get_return_slots_qa_intent_flow("q", "a", "s", "i", "f") == []
        assert get_return_slots_qa_intent_flow_followed("q", "s", "i", 1, "l", "f", "lq") == []
        assert clear_slots() == []

    # Extra fallback patch for remaining isolated structural targets
    with patch(f"{PATCH_TARGET}.log_info_text", side_effect=ValueError("Simulated Error")):
        assert get_return_slots_for_conversations({"test": "val"}) == []


# ==============================================================================
# 3. TRACKER CONVERSATION HISTORY ANALYSIS
# ==============================================================================

@pytest.mark.parametrize("events_list, expected_second_last", [
    ([], None),
    ([{"event": "user", "text": "Hello"}], None),
    ([{"event": "user", "text": "Q1"}, {"event": "bot", "text": "A1"}, {"event": "user", "text": "Q2"}], "Q1"),
    ([{"event": "user", "text": "Q1"}, {"event": "user", "text": ""}, {"event": "user", "text": "Q2"}], "Q1")
])
def test_get_conversational_slots(mock_tracker, events_list, expected_second_last):
    mock_tracker.events = events_list
    result = get_conversational_slots(mock_tracker)
    assert result == expected_second_last


def test_get_slot_sscomp(mock_tracker):
    assert get_slot_sscomp(mock_tracker) == "architecture_software"
    mock_tracker.get_slot.assert_called_once_with("sscomp")


# ==============================================================================
# 4. RAW DICTIONARY GENERATION DTO METRIC BUILDERS
# ==============================================================================

def test_get_slots_to_set():
    res = get_slots_to_set("comp_val", "Q1", "Q2", "Ans", "intent", 1)
    assert res["sscomp"] == "comp_val"
    assert res["active_flow"] is None


def test_get_slots_to_set_json():
    res = get_slots_to_set_json("sess_val", "spec_val", "grade_val", "Q1", "Q2", "Ans", "intent", 2)
    assert res["session"] == "sess_val"
    assert res["grade"] == "grade_val"


def test_get_slots_to_set_eval_pj():
    res = get_slots_to_set_eval_pj("comp_val", "spec_val", "Q1", "Q2", "Ans", "intent", 1)
    assert res["sscomp"] == "comp_val"
    assert res["speciality"] == "spec_val"


def test_get_slots_to_set_last_answer_flow():
    res = get_slots_to_set_last_answer_flow("flow_xyz", "Target validation text")
    assert res["active_flow"] == "flow_xyz"
    assert res["last_answer"] == "Target validation text"


def test_get_slots_to_set_maintain_conv():
    res = get_slots_to_set_maintain_conv("Q1", "Q2", "Ans", "intent", 3)
    assert res["last_last_question"] == "Q1"
    assert res["forward_level"] == 3


def test_get_slots_to_set_maintain_active_flow():
    res = get_slots_to_set_maintain_active_flow("Q1", "Q2", "Ans", "intent", 1, "active_flow_state")
    assert res["active_flow"] == "active_flow_state"


def test_get_slots_to_set_maintain_conv_qa():
    res = get_slots_to_set_maintain_conv_qa("Q1", "Q2", "intent", 2)
    assert "last_answer" not in res
    assert res["last_question"] == "Q2"