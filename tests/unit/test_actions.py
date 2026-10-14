"""
tests/unit/test_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from actions.actions import (
    remove_excluded_patterns,
    check_is_excluded,
    get_bilan_final_results,
    safe_get_note,
    classify_results,
    get_payload,
    get_semantic_random_reply,
    generate_composante_buttons,
    call_llm_with_retry,
    ensure_complete_bullets,
    append_friendly_intro_to_answer,
    contains_number,
    clean_response,
    format_response_steps,
    format_response_all,
    format_response_old,
    remove_trailing_stars,
    clean_llm_response,
    return_to_next_line,
    get_formatted_next_line,
    append_friendly_intro_to_answer_block,
    get_name,
    get_extracted_slots,
    get_list_extracted_slots,
    reformulate_session_if_hallucinate,
    ajuster_session_passage_grade,
    normalize_text,
    normalize_synonyms,
    normalize_text_strict,
    detecter_mots_cles,
    get__decision_mode__last_intent
)
from actions.constants.ActiveIntents import ActiveIntents
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
    # "est-ce qu" et "sont-ils" doivent être supprimés
    result = remove_excluded_patterns(sentence)
    assert "est-ce qu" not in result
    assert "sont-ils" not in result


def test_check_is_excluded():
    assert check_is_excluded("Sont-ils compatibles ?") is True
    assert check_is_excluded("Bonjour monsieur") is False


def test_ensure_complete_bullets():
    text = "- Ligne valide.\n- Ligne coupée\n- Autre ligne valide!"
    result = ensure_complete_bullets(text)
    assert "- Ligne valide." in result
    assert "- Ligne coupée" not in result
    assert "- Autre ligne valide!" in result


def test_contains_number():
    assert contains_number("Session 2024") is True
    assert contains_number("Session normale") is False


def test_clean_response():
    assert clean_response("Réponse valide. Texte coupé sans fin") == "Réponse valide."
    assert clean_response("Pas de point du tout") == "Pas de point du tout"

def test_clean_llm_response():
    text = "Ligne 1\n\n\nLigne 2\n   \nLigne 3"
    result = clean_llm_response(text)
    assert "\n\n\n" not in result


def test_return_to_next_line():
    text = "Première phrase. Deuxième phrase."
    result = return_to_next_line(text)
    assert "Première phrase.\n\nDeuxième phrase." in result


def test_get_formatted_next_line():
    text = "Partie 1. Partie 2"
    assert get_formatted_next_line(text) == "Partie 1.\nPartie 2."


def test_append_friendly_intro_to_answer_block():
    result = append_friendly_intro_to_answer_block("Réponse brute")
    assert result.startswith("```")
    assert result.endswith("```")
    assert "Réponse brute" in result


def test_get_name():
    assert get_name("/path/to/hierarchy_score.pdf") == "score.pdf"
    assert get_name("/path/to/normal_file.pdf") == "normal_file.pdf"


# ==============================================================================
# TESTS: HIERARCHY & RESULTS CLASSIFICATION
# ==============================================================================
def test_get_bilan_final_results(mock_dispatcher):
    with patch(f"{PATCH_TARGET}.send_message_forwarded_by_buttons") as mock_send:
        get_bilan_final_results(mock_dispatcher)
        mock_send.assert_called_once()


def test_safe_get_note():
    notes = {"11": {"labelSSComp": "Maths", "noteSSComp": 15, "baremeSSComp": 20}}
    assert safe_get_note(notes, "11") == {"name": "Maths", "score": 15, "bareme": 20}
    assert safe_get_note(notes, "99") is None


def test_classify_results():
    results = {
        "allCompNotes": {
            "1": {"labelAllComp": "Composante Principale 1", "noteAllComp": 14, "baremeAllComp": 20}
        },
        "notes": {
            "1": {"labelSSComp": "Ignore Me C1", "noteSSComp": 14, "baremeSSComp": 20},
            "11": {"labelSSComp": "Sous-composante 1.1", "noteSSComp": 14, "baremeSSComp": 20}
        }
    }
    hierarchy = classify_results(results)
    assert "Composante Principale 1" in hierarchy
    assert "11" in hierarchy["Composante Principale 1"]
    assert hierarchy["Composante Principale 1"]["11"]["name"] == "Sous-composante 1.1"


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
# TESTS: LLM INFERENCE WITH RETRY
# ==============================================================================
@pytest.mark.asyncio
async def test_call_llm_with_retry_success(mock_dispatcher):
    mock_llm = AsyncMock(return_value="LLM Response Success")
    res = await call_llm_with_retry(mock_llm, mock_dispatcher, "Prompt", "label", {})
    assert res == "LLM Response Success"
    assert mock_llm.call_count == 1


@pytest.mark.asyncio
async def test_call_llm_with_retry_timeout_then_success(mock_dispatcher):
    mock_llm = AsyncMock()
    mock_llm.side_effect = [TimeoutError("Timeout !"), "Fallback Success"]

    res = await call_llm_with_retry(mock_llm, mock_dispatcher, "Prompt", "label", {})
    assert res == "Fallback Success"
    assert mock_llm.call_count == 2


@pytest.mark.asyncio
async def test_call_llm_with_retry_total_failure(mock_dispatcher):
    mock_llm = AsyncMock(side_effect=RuntimeError("Fatal Error"))

    with patch(f"{PATCH_TARGET}.exception_llm_err", return_value="Erreur Utilisateur"), \
            patch(f"{PATCH_TARGET}.exception_llm_err_dsi") as mock_dsi:
        with pytest.raises(RuntimeError, match="Erreur Utilisateur"):
            await call_llm_with_retry(mock_llm, mock_dispatcher, "Prompt", "label", {})
        mock_dsi.assert_called_once()


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

def test_format_response_steps_and_all():
    text = "1. Etape Un\n2. Etape Deux"
    assert "1. Etape Un" in format_response_steps(text)

    text_sentences = "Phrase un. Phrase deux."
    formatted = format_response_all(text_sentences)
    assert "\n" in formatted

def test_get_list_extracted_slots(mock_tracker):
    mock_tracker.get_latest_entity_values.return_value = ["IT", "IT", "Meca"]
    res = get_list_extracted_slots(mock_tracker, "speciality")
    assert res == ["IT", "Meca"]  # Doublons supprimés via dict.fromkeys


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


def test_normalize_synonyms():
    assert normalize_synonyms("Résolution Élevée") == "resolution elevee"


def test_normalize_text_strict():
    assert normalize_text_strict("  Excellent, Éléphant; Séquence!  ") == "excellent elephant sequence"


def test_detecter_mots_cles():
    assert detecter_mots_cles("J'adore le framework Spring Boot", ["spring", "react"]) is True
    assert detecter_mots_cles("Aucun mot cible ici", ["spring", "react"]) is False


def test_remove_trailing_stars():
    # Ajout du saut de ligne \n requis par le pattern r'\n\s*\*\*\s*$'
    assert remove_trailing_stars("Texte avec étoiles\n**") == "Texte avec étoiles"

    # Vérification qu'une chaîne sans retour à la ligne + étoiles reste intacte
    assert remove_trailing_stars("Texte normal") == "Texte normal"


def test_format_response_old():
    # Chaîne nominale se terminant correctement par un point
    # La fonction conserve les points via lookbehind et ajoute un séparateur '.\n' plus un point final.
    assert format_response_old("Phrase un. Phrase deux.") == "Phrase un..\nPhrase deux.."

    # Test du comportement de troncature si pas de point final
    assert format_response_old("Phrase un. Phrase deux coupée ici") == "Phrase un.."


def test_reformulate_session_if_hallucinate():
    # Cas nominal : l'année précède directement l'hallucination "-2session"
    assert reformulate_session_if_hallucinate(
        "Erreur session 2025-2session observée") == "Erreur session 2025-2026 observée"

    # Vérification qu'une chaîne sans ce pattern spécifique n'est pas altérée
    assert reformulate_session_if_hallucinate("Texte normal en 2025") == "Texte normal en 2025"