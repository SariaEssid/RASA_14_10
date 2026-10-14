"""
tests/unit/test_semantic.py

@author ESSID Saria | Copyright (c) 2026. ESPRIT
"""

import json
from unittest.mock import MagicMock, patch, mock_open

import pytest

from actions.semantic import semantic

# Module level target patch constant
PATCH_TARGET = "actions.semantic.semantic"


@pytest.fixture(autouse=True)
def reset_singletons():
    """Resets global singletons in the module before and after each test run."""
    semantic._index = None
    semantic._answers = None
    semantic._model = None
    semantic._index_mtime = 0
    semantic._answers_mtime = 0
    semantic._model_loaded = False
    yield
    semantic._index = None
    semantic._answers = None
    semantic._model = None
    semantic._index_mtime = 0
    semantic._answers_mtime = 0
    semantic._model_loaded = False


## =====================================================================
## 1. FAISS INDEX MANAGEMENT TESTS
## =====================================================================

def test_load_index_safely_missing_file():
    """Verifies _load_index_safely raises FileNotFoundError when index file does not exist."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="FAISS index not found"):
            # noinspection PyProtectedAccess
            semantic._load_index_safely("dummy_path")


def test_load_index_safely_invalid_dimensions():
    """Verifies _load_index_safely raises ValueError for zero vectors or zero dimensions."""
    mock_index = MagicMock()
    mock_index.ntotal = 0
    mock_index.d = 0

    with patch("os.path.exists", return_value=True), \
            patch("faiss.read_index", return_value=mock_index):
        with pytest.raises(ValueError, match="Invalid FAISS index"):
            # noinspection PyProtectedAccess
            semantic._load_index_safely("dummy_path")


def test_load_index_safely_search_validation_fails():
    """Verifies that an exception during the validation search re-raises properly."""
    mock_index = MagicMock()
    mock_index.ntotal = 10
    mock_index.d = 384
    mock_index.search.side_effect = RuntimeError("FAISS internal crash")

    with patch("os.path.exists", return_value=True), \
            patch("faiss.read_index", return_value=mock_index), \
            patch(f"{PATCH_TARGET}.log.error") as mock_log_err:
        with pytest.raises(RuntimeError, match="FAISS internal crash"):
            # noinspection PyProtectedAccess
            semantic._load_index_safely("dummy_path")
        mock_log_err.assert_called_once()


def test_get_index_successful_initial_load():
    """Verifies successful lazy loading and validation of a valid FAISS index."""
    mock_index = MagicMock()
    mock_index.ntotal = 100
    mock_index.d = 384

    with patch(f"{PATCH_TARGET}._load_index_safely", return_value=mock_index) as mock_load, \
            patch(f"{PATCH_TARGET}._get_file_mtime", return_value=12345.6), \
            patch(f"{PATCH_TARGET}._needs_reload", return_value=True):
        index = semantic.get_index()
        assert index == mock_index
        assert semantic._index_mtime == 12345.6
        mock_load.assert_called_once_with(semantic.FAISS_INDEX_PATH)


def test_get_index_cached_health_check_failed_reloads():
    """Verifies that if cached index ntotal drops to 0, health check reloads it."""
    mock_old_index = MagicMock()
    mock_old_index.ntotal = 0  # Invalid state triggers health fallback
    mock_old_index.d = 384

    mock_new_index = MagicMock()
    mock_new_index.ntotal = 150
    mock_new_index.d = 384

    semantic._index = mock_old_index
    semantic._index_mtime = 1000.0

    with patch(f"{PATCH_TARGET}._needs_reload", return_value=False), \
            patch(f"{PATCH_TARGET}._load_index_safely", return_value=mock_new_index) as mock_load, \
            patch(f"{PATCH_TARGET}._get_file_mtime", return_value=2000.0):
        index = semantic.get_index()
        assert index == mock_new_index
        assert semantic._index_mtime == 2000.0
        mock_load.assert_called_once()


def test_get_index_cached_exception_reloads():
    """Verifies that an unexpected exception evaluating cached index properties triggers reload."""
    mock_corrupted_index = MagicMock()
    # Triggering an exception during property evaluation
    type(mock_corrupted_index).ntotal = property(lambda self: raise_(ValueError("Corrupted properties")))

    mock_recovered_index = MagicMock()
    mock_recovered_index.ntotal = 200
    mock_recovered_index.d = 384

    semantic._index = mock_corrupted_index
    semantic._index_mtime = 500.0

    def raise_(ex): raise ex

    with patch(f"{PATCH_TARGET}._needs_reload", return_value=False), \
            patch(f"{PATCH_TARGET}._load_index_safely", return_value=mock_recovered_index), \
            patch(f"{PATCH_TARGET}._get_file_mtime", return_value=600.0), \
            patch(f"{PATCH_TARGET}.log.error") as mock_log_err:
        index = semantic.get_index()
        assert index == mock_recovered_index
        mock_log_err.assert_called_once()


## =====================================================================
## 2. ANSWERS JSON FILE HANDLING TESTS
## =====================================================================

def test_load_answers_safely_missing_file():
    """Verifies _load_answers_safely raises FileNotFoundError when answers file is missing."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Answers file not found"):
            # noinspection PyProtectedAccess
            semantic._load_answers_safely("dummy_path")


def test_load_answers_safely_invalid_json():
    """Verifies JSONDecodeError is caught, logged, and re-raised."""
    with patch("os.path.exists", return_value=True), \
            patch("builtins.open", mock_open(read_data="{ invalid json ")), \
            patch(f"{PATCH_TARGET}.log.error") as mock_log_err:
        with pytest.raises(json.JSONDecodeError):
            # noinspection PyProtectedAccess
            semantic._load_answers_safely("dummy_path")
        mock_log_err.assert_called_once()


def test_load_answers_safely_invalid_type():
    """Verifies that answers JSON containing a literal type other than array/object raises ValueError."""
    with patch("os.path.exists", return_value=True), \
            patch("builtins.open", mock_open(read_data="12345")):
        with pytest.raises(ValueError, match="Answers file must contain JSON array or object"):
            # noinspection PyProtectedAccess
            semantic._load_answers_safely("dummy_path")


def test_get_answers_lazy_load():
    """Verifies successful reading and caching of a dictionary structural payload."""
    mock_data = {"q1": "answer1", "q2": "answer2"}

    with patch(f"{PATCH_TARGET}._load_answers_safely", return_value=mock_data) as mock_load, \
            patch(f"{PATCH_TARGET}._get_file_mtime", return_value=555.5), \
            patch(f"{PATCH_TARGET}._needs_reload", return_value=True):
        answers = semantic.get_answers()
        assert answers == mock_data
        assert semantic._answers_mtime == 555.5
        mock_load.assert_called_once()


## =====================================================================
## 3. MODEL TRANSFORMER LOADING TESTS
## =====================================================================

def test_load_model_safely_empty_embedding_validation():
    """Verifies that if SentenceTransformer generates empty metrics array, a ValueError is raised."""
    mock_transformer = MagicMock()
    mock_transformer.encode.return_value = []

    with patch(f"{PATCH_TARGET}.SentenceTransformer", return_value=mock_transformer), \
            patch(f"{PATCH_TARGET}.log.error") as mock_log_err:
        with pytest.raises(ValueError, match="Model produced empty embedding"):
            # noinspection PyProtectedAccess
            semantic._load_model_safely("dummy_model_name")
        mock_log_err.assert_called_once()


def test_get_model_cached_retrieval():
    """Verifies that if model_loaded is True, the model constructor is not invoked again."""
    mock_model_instance = MagicMock()
    semantic._model = mock_model_instance
    semantic._model_loaded = True

    with patch(f"{PATCH_TARGET}._load_model_safely") as mock_load:
        model = semantic.get_model()
        assert model == mock_model_instance
        mock_load.assert_not_called()


## =====================================================================
## 4. RELOAD, UTILITIES, AND PIPELINE CLEANUP TESTS
## =====================================================================

def test_get_file_mtime_os_error_fallback():
    """Verifies that an internal OSError returning from filesystem maps gracefully to 0."""
    with patch("os.path.getmtime", side_effect=OSError("Drive unreadable")):
        # noinspection PyProtectedAccess
        mtime = semantic._get_file_mtime("any_path")
        assert mtime == 0


def test_reload_all_resources_execution():
    """Verifies thread-safe clearing and orchestration loops of resources reload."""
    with patch(f"{PATCH_TARGET}.get_index") as mock_idx, \
            patch(f"{PATCH_TARGET}.get_answers") as mock_ans, \
            patch(f"{PATCH_TARGET}.get_model") as mock_mdl:
        status = semantic.reload_all_resources()
        assert status is True

        # Verify singletons were reset before thread triggers
        assert semantic._index is None
        assert semantic._answers is None
        assert semantic._model is None

        mock_idx.assert_called_once()
        mock_ans.assert_called_once()
        mock_mdl.assert_called_once()


def test_get_resource_stats_unloaded_vs_loaded():
    """Tests schema shapes returned by monitoring utility when modules are empty vs populated."""
    # Scenario A: Empty/Unloaded State
    stats = semantic.get_resource_stats()
    assert stats["faiss_index"]["loaded"] is False
    assert stats["faiss_index"]["vectors"] == 0
    assert stats["answers"]["count"] == 0

    # Scenario B: Fully Populated State
    mock_index = MagicMock()
    mock_index.ntotal = 42
    mock_index.d = 384
    semantic._index = mock_index
    semantic._answers = ["ans1", "ans2", "ans3"]
    semantic._model = MagicMock()

    stats_loaded = semantic.get_resource_stats()
    assert stats_loaded["faiss_index"]["loaded"] is True
    assert stats_loaded["faiss_index"]["vectors"] == 42
    assert stats_loaded["faiss_index"]["dimensions"] == 384
    assert stats_loaded["answers"]["count"] == 3
    assert stats_loaded["model"]["loaded"] is True


def test_cleanup_resources_deletes_references():
    """Verifies explicit cleanup handles reference deletion without crashing."""
    semantic._index = MagicMock()
    semantic._model = MagicMock()

    semantic.cleanup_resources()
    # If it executes without NameError or crash, it passes cleanly