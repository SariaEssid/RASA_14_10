"""
tests/unit/test_embedding_loader.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import os
import pytest
from unittest.mock import MagicMock, patch
import actions.utils.embedding_loader as embedding_loader
from actions.utils.embedding_loader import get_embedder


@pytest.fixture(autouse=True)
def reset_embedder_global():
    """
    Resets the global _embedder variable before every test
    to ensure isolation and clean lazy-loading states.
    """
    embedding_loader._embedder = None
    yield
    embedding_loader._embedder = None


@patch("actions.utils.embedding_loader.SentenceTransformer")
@patch("actions.utils.embedding_loader.settings")
def test_get_embedder_lazy_initialization(mock_settings, mock_sentence_transformer):
    """
    Test that the embedder is initialized correctly on the first call
    using the model name from settings.
    """
    # Arrange
    mock_settings.semantic_model_name = "test-model-name"
    mock_instance = MagicMock()
    mock_sentence_transformer.return_value = mock_instance

    # Act
    result = get_embedder()

    # Assert
    mock_sentence_transformer.assert_called_once_with("test-model-name")
    assert result == mock_instance


@patch("actions.utils.embedding_loader.SentenceTransformer")
@patch("actions.utils.embedding_loader.settings")
def test_get_embedder_returns_cached_instance(mock_settings, mock_sentence_transformer):
    """
    Test that subsequent calls to get_embedder return the cached instance
    without instantiating SentenceTransformer again (Singleton behavior).
    """
    # Arrange
    mock_settings.semantic_model_name = "all-MiniLM-L6-v2"
    mock_instance = MagicMock()
    mock_sentence_transformer.return_value = mock_instance

    # Act
    first_call = get_embedder()
    second_call = get_embedder()

    # Assert
    mock_sentence_transformer.assert_called_once()  # Only called the first time
    assert first_call == mock_instance
    assert second_call == mock_instance
    assert first_call is second_call  # Explicitly verifies identical memory reference


@patch("actions.utils.embedding_loader.settings")
@patch.dict(os.environ, {"HF_HUB_OFFLINE": "1"})
def test_get_embedder_offline_mode_hf_hub(mock_settings):
    """
    Test that environment variables are set correctly when HF_HUB_OFFLINE is "1".
    """
    # Arrange
    mock_settings.semantic_model_name = "all-MiniLM-L6-v2"

    # Act
    get_embedder()

    # Assert
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"


@patch("actions.utils.embedding_loader.settings")
@patch.dict(os.environ, {"TRANSFORMERS_OFFLINE": "1"})
def test_get_embedder_offline_mode_transformers(mock_settings):
    """
    Test that environment variables are set correctly when TRANSFORMERS_OFFLINE is "1".
    """
    # Arrange
    mock_settings.semantic_model_name = "all-MiniLM-L6-v2"

    # Act
    get_embedder()

    # Assert
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"


@patch("actions.utils.embedding_loader.SentenceTransformer")
def test_get_embedder_fallback_default_model(mock_sentence_transformer):
    """
    Test fallback to default model name if semantic_model_name is missing from settings.
    """
    # Arrange
    with patch("actions.utils.embedding_loader.settings", spec=object):
        # Act
        get_embedder()
        # Assert
        mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2")