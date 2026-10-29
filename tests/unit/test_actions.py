"""
tests/unit/test_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from actions.actions import (
    remove_excluded_patterns,
    check_is_excluded,
    get_payload,
    get_semantic_random_reply,
    generate_composante_buttons,
    clean_response,
    clean_llm_response,
    reformulate_session_if_hallucinate,
    ajuster_session_passage_grade,
    normalize_text,
    normalize_text_strict,
    get__decision_mode__last_intent
)
from actions.semantic.faiss_ranking import FAQCandidate

# Target namespace pour les patchs
PATCH_TARGET = "actions.actions"


# ==============================================================================
# FIXTURES
# ==============================================================================
@pytest.fixture
def mock_dispatcher():
    return MagicMock()


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.get_slot.return_value = None
    tracker.get_latest_entity_values.return_value = []
    return tracker


# ==============================================================================
# TESTS: TEXT CLEANING & PATTERNS
# ==============================================================================
def test_remove_excluded_patterns():
    sentence = "Est-ce qu'il y a des conditions si sont-ils présents ?"
    result = remove_excluded_patterns(sentence)
    assert "est-ce qu" not in result
    assert "sont-ils" not in result


def test_check_is_excluded():
    assert check_is_excluded("Sont-ils compatibles ?") is True
    assert check_is_excluded("Bonjour monsieur") is False

def test_clean_response():
    assert clean_response("Réponse valide. Texte coupé sans fin") == "Réponse valide."
    assert clean_response("Pas de point du tout") == "Pas de point du tout"

def test_clean_llm_response():
    text = "Ligne 1\n\n\nLigne 2\n   \nLigne 3"
    result = clean_llm_response(text)
    assert "\n\n\n" not in result

# ==============================================================================
# TESTS: PAYLOADS & BUTTONS
# ==============================================================================
def test_get_payload():
    payload = get_payload("user123", "sess999", "Question", "intent_test", 0.98)
    assert payload["userId"] == "user123"
    assert payload["sessionId"] == "sess999"
    assert payload["userInput"] == "Question"
    assert payload["rasaIntent"] == "intent_test"
    assert payload["confidence"] == 0.98
    assert "messageExchangeDate" in payload


def test_generate_composante_buttons():
    with patch(f"{PATCH_TARGET}.ALL_COMPOSANTES_PRINCIPALES", ["CompA", "CompB"]):
        buttons = generate_composante_buttons()
        assert len(buttons) == 3  # 2 Composantes + 1 Bouton Retour
        assert buttons[-1]["title"] == "🔙 Retourner au Mini-Guide"

# ==============================================================================
# TESTS: FAQCANDIDATE SEMANTIC RANKING
# ==============================================================================
def test_get_semantic_random_reply_empty():
    with patch(f"{PATCH_TARGET}.BOT_MESSAGES", {"no_response": "Désolé, aucune réponse"}):
        reply = get_semantic_random_reply([], "label", "input")
        assert reply == "Désolé, aucune réponse"


def test_get_semantic_random_reply_with_candidates():
    candidates_data = [
        {"id_faq": 1, "userInput": "Question 1", "botResponse": "Réponse 1", "weight": 1.0},
        {"id_faq": 2, "userInput": "Question 2", "botResponse": "Réponse 2", "weight": 1.0}
    ]

    mock_ranked = [(FAQCandidate(1, "Question 1", "Réponse 1", Decimal("1.0")), 0.95)]

    with patch(f"{PATCH_TARGET}.rank_candidates", return_value=mock_ranked), \
            patch(f"{PATCH_TARGET}.pick_weighted_answer", return_value="Réponse 1"):
        reply = get_semantic_random_reply(candidates_data, "label", "Question 1")
        assert reply == "Réponse 1"

def test_get_detaillevel_lastintent(mock_tracker):
    mock_tracker.get_slot.side_effect = lambda key: "forward_val" if key == "forward_level" else "intent_val"
    level, intent = get__decision_mode__last_intent("label", mock_tracker)
    assert level == "forward_val"
    assert intent == "intent_val"


# ==============================================================================
# TESTS: STRATEGIES DE NORMALISATION & TEXT MATCHING
# ==============================================================================
def test_ajuster_session_passage_grade():
    assert ajuster_session_passage_grade("Session 2024-2session") == "Session 2024-2025"

def test_normalize_text():
    assert normalize_text("L’Élève Secrétaire") == "l'eleve secretaire"

def test_normalize_text_strict():
    assert normalize_text_strict("  Excellent, Éléphant; Séquence!  ") == "excellent elephant sequence"

def test_reformulate_session_if_hallucinate():
    # Cas nominal : l'année précède directement l'hallucination "-2session"
    assert reformulate_session_if_hallucinate(
        "Erreur session 2025-2session observée") == "Erreur session 2025-2026 observée"

    # Vérification qu'une chaîne sans ce pattern spécifique n'est pas altérée
    assert reformulate_session_if_hallucinate("Texte normal en 2025") == "Texte normal en 2025"