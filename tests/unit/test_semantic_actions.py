# noinspection PyPackageRequirements
"""
@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import json
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

import numpy as np
import pytest
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.semantic.faiss_ranking import rank_candidates, pick_weighted_answer
from actions.semantic.semantic import (
    get_index,
    get_answers,
    get_resource_stats
)
# Target under test imports
from actions.semantic.semantic_actions import (
    ActionSemanticQA,
    encode_for_faiss,
    safe_faiss_search,
    flatten_events,
    is_followup
)
from actions.utils.models import FAQCandidate

PATCH_TARGET = "actions.semantic.semantic_actions"
SEMANTIC_MODULE = "actions.semantic.semantic"


# ==============================================================================
# FIXTURES SETUP
# ==============================================================================

@pytest.fixture
def dispatcher() -> CollectingDispatcher:
    return CollectingDispatcher()


@pytest.fixture
def tracker() -> MagicMock:
    tracker_mock = MagicMock(spec=Tracker)
    tracker_mock.latest_message = {
        "text": "Comment se déroule le passage de grade ?",
        "intent": {"name": "ask_procedure", "confidence": 0.95}
    }
    tracker_mock.sender_id = "student_saria"
    tracker_mock.get_slot = MagicMock(side_effect=lambda key: {
        "session_id": "session_123",
        "active_flow": "grade_passage_flow",
        "sscomp": None,
        "last_question": "Quelle est la procédure ?"
    }.get(key))
    return tracker_mock


@pytest.fixture(autouse=True)
def reset_semantic_singletons():
    """Resets global state across tests to avoid mutation bleed."""
    import actions.semantic.semantic as sem

    # Directly modify the module-level variables
    # No need for a separate local function or complex return statements
    sem._index = None
    sem._answers = None
    sem._model = None
    sem._index_mtime = 0
    sem._answers_mtime = 0
    sem._model_loaded = False

    yield


def reset_for_tests():
    """Expose a controlled way to reset state for testing."""
    _index = None
    _answers = None
    _model = None
    _index_mtime = 0
    _answers_mtime = 0
    _model_loaded = False
    return _index, _answers, _model, _index_mtime, _answers_mtime, _model_loaded
# ==============================================================================
# 1. ActionSemanticQA ACTIONS TEST CASES
# ==============================================================================

@pytest.mark.asyncio
async def test_action_semantic_qa_name():
    action = ActionSemanticQA()
    assert action.name() == "action_semantic_qa"


@pytest.mark.asyncio
async def test_action_semantic_qa_exit_on_empty_or_long(dispatcher, tracker):
    action = ActionSemanticQA()
    with patch(f"{PATCH_TARGET}.exit_for_empty_and_long_question", return_value=True):
        events = await action.run(dispatcher, tracker, {})
        assert events == []

# ==============================================================================
# 2. UTILITIES & MATH LAYER MOCK VALIDATIONS
# ==============================================================================

def test_encode_for_faiss_dimensions():
    mock_model = MagicMock()
    mock_model.encode = MagicMock(return_value=np.array([0.1, 0.2, 0.3], dtype=np.float32))

    embedding = encode_for_faiss(mock_model, "Test input normalization")
    assert embedding.ndim == 2
    assert embedding.shape == (1, 3)


def test_safe_faiss_search_empty_index_raise():
    with pytest.raises(RuntimeError, match="FAISS index not loaded or empty"):
        safe_faiss_search(None, np.array([[0.1]]), k=1)


def test_flatten_events_nested_structures():
    nested_events = [{"event": "slot"}, [{"event": "bot"}, {"event": "restart"}], {"event": "user"}]
    flat = flatten_events(nested_events)
    assert len(flat) == 4
    assert [e["event"] for e in flat] == ["slot", "bot", "restart", "user"]

# ==============================================================================
# 3. SINGLETON RESOURCE MANAGER VALIDATION (semantic.py)
# ==============================================================================

@patch(f"{SEMANTIC_MODULE}.os.path.exists", return_value=True)
@patch(f"{SEMANTIC_MODULE}.faiss.read_index")
@patch(f"{SEMANTIC_MODULE}._get_file_mtime", return_value=1000.0)
def test_get_index_thread_safe_instantiation(_mock_mtime, mock_read_index, _mock_exists):
    mock_faiss_idx = MagicMock()
    mock_faiss_idx.ntotal = 10
    mock_faiss_idx.d = 128
    mock_read_index.return_value = mock_faiss_idx

    idx = get_index()
    assert idx.ntotal == 10
    assert mock_read_index.call_count == 1

    idx_cached = get_index()
    assert idx_cached == idx
    assert mock_read_index.call_count == 1


@patch(f"{SEMANTIC_MODULE}.os.path.exists", return_value=True)
def test_get_answers_json_parsing(_mock_exists):
    mock_data = json.dumps({"0": "Answer Alpha", "1": "Answer Beta"})
    with patch("builtins.open", mock_open(read_data=mock_data)):
        answers = get_answers()
        assert isinstance(answers, dict)
        assert answers["0"] == "Answer Alpha"


def test_get_resource_stats_reporting():
    stats = get_resource_stats()
    assert "faiss_index" in stats
    assert "answers" in stats
    assert "model" in stats


# ==============================================================================
# 4. FAISS RANKING & WEIGHTED SAMPLING ALGORITHMS
# ==============================================================================

@patch("actions.semantic.faiss_ranking.get_embedder")
@patch("actions.semantic.faiss_ranking.util.cos_sim")
def test_rank_candidates_sorting_logic(mock_cos_sim, mock_get_embedder):
    mock_model = MagicMock()
    mock_get_embedder.return_value = mock_model
    mock_cos_sim.return_value = np.array([[0.4, 0.9]])

    cand_a = MagicMock(spec=FAQCandidate)
    cand_a.userInput = "Low similarity matching entry"
    cand_b = MagicMock(spec=FAQCandidate)
    cand_b.userInput = "High similarity matching entry"

    ranked = rank_candidates("User request", [cand_a, cand_b])

    assert len(ranked) == 2
    assert ranked[0][0] == cand_b
    assert ranked[0][1] == 0.9


def test_pick_weighted_answer_selection():
    cand_heavy = MagicMock(spec=FAQCandidate)
    cand_heavy.botResponse = "Heavy Response"
    cand_heavy.weight = 100.0

    cand_light = MagicMock(spec=FAQCandidate)
    cand_light.botResponse = "Light Response"
    cand_light.weight = 0.0

    selected = pick_weighted_answer([cand_heavy, cand_light])
    assert selected == "Heavy Response"


# ==============================================================================
# 5. EXPANDED EDGE CASES FOR MAXIMUM LINE COVERAGE
# ==============================================================================

# ==============================================================================
# 6. FINAL SCENARIOS FOR MAXIMUM COMPONENT COVERAGE
# ==============================================================================

def test_safe_faiss_search_index_error_fallback():
    mock_index = MagicMock()
    mock_index.ntotal = 0
    dummy_embedding = np.zeros((1, 384), dtype=np.float32)

    with pytest.raises(RuntimeError, match="FAISS index not loaded or empty"):
        safe_faiss_search(mock_index, dummy_embedding, k=1)


def test_get_resource_stats_missing_file_or_corrupted():
    with patch("os.path.exists", return_value=False), \
            patch(f"{PATCH_TARGET}.log_info_text"):
        stats = get_resource_stats()

        assert "answers" in stats
        assert "faiss_index" in stats
        assert stats["answers"]["loaded"] is False
        assert stats["faiss_index"]["dimensions"] == 0