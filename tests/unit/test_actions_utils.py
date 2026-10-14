"""
tests/unit/test_actions_utils.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.actions import (
    remove_excluded_patterns,
    check_is_excluded,
    safe_get_note,
    classify_results,
    get_payload,
    ensure_complete_bullets,
    contains_number,
    clean_response,
    format_response_steps,
    format_response_all,
    remove_trailing_stars,
    clean_llm_response,
    return_to_next_line,
    get_formatted_next_line,
    get_name,
    ajuster_session_passage_grade,
    reformulate_session_if_hallucinate,
    normalize_text,
    normalize_synonyms,
    normalize_text_strict,
    detecter_mots_cles
)


def test_remove_excluded_patterns():
    text = "Est-ce qu il existe une session ?"
    result = remove_excluded_patterns(text)

    assert "est-ce qu" not in result.lower()


def test_check_is_excluded_true():
    assert check_is_excluded("est-ce qu il existe ?") is True


def test_check_is_excluded_false():
    assert check_is_excluded("bonjour") is False


def test_safe_get_note_found():
    notes = {
        "1": {
            "labelSSComp": "Math",
            "noteSSComp": 15,
            "baremeSSComp": 20
        }
    }

    result = safe_get_note(notes, "1")

    assert result["name"] == "Math"
    assert result["score"] == 15
    assert result["bareme"] == 20


def test_safe_get_note_missing():
    notes = {}

    assert safe_get_note(notes, "x") is None


def test_classify_results():
    results = {
        "allCompNotes": {
            "1": {
                "labelAllComp": "Comp1",
                "noteAllComp": 10,
                "baremeAllComp": 20
            }
        },
        "notes": {
            "11": {
                "labelSSComp": "Sub",
                "noteSSComp": 5,
                "baremeSSComp": 10
            }
        }
    }

    hierarchy = classify_results(results)

    assert "Comp1" in hierarchy


def test_get_payload():
    payload = get_payload(
        "u1",
        "s1",
        "hello",
        "intent_x",
        0.95
    )

    assert payload["userId"] == "u1"
    assert payload["sessionId"] == "s1"
    assert payload["confidence"] == 0.95


def test_ensure_complete_bullets():
    text = "- valid.\n- invalid"

    result = ensure_complete_bullets(text)

    assert "- valid." in result
    assert "- invalid" not in result


def test_contains_number_true():
    assert contains_number("abc123") is True


def test_contains_number_false():
    assert contains_number("abc") is False


def test_clean_response():
    result = clean_response("hello.world.test")

    assert result.endswith(".")


def test_format_response_steps():
    text = "1.\nhello."

    result = format_response_steps(text)

    assert "1. hello." in result


def test_format_response_all():
    text = "Hello. World."

    result = format_response_all(text)

    assert "\n" in result


def test_remove_trailing_stars():
    result = remove_trailing_stars("hello\n**")

    assert result == "hello"


def test_clean_llm_response():
    text = "\n\nhello\n\n\nworld"

    result = clean_llm_response(text)

    assert "hello" in result
    assert "world" in result


def test_return_to_next_line():
    result = return_to_next_line("Hello.World.")

    assert "\n\n" in result


def test_get_formatted_next_line():
    result = get_formatted_next_line("A.B.C")

    assert ".\n" in result


def test_get_name():
    result = get_name("/tmp/hierarchy_score.pdf")

    assert result == "score.pdf"


def test_ajuster_session_passage_grade():
    result = ajuster_session_passage_grade(
        "session 2024-2abc"
    )

    assert "2024-2025" in result


def test_reformulate_session_if_hallucinate():
    result = reformulate_session_if_hallucinate(
        "session 2024-2abc"
    )

    assert "2024-2025" in result


def test_normalize_text():
    result = normalize_text("École")

    assert result == "ecole"


def test_normalize_synonyms():
    result = normalize_synonyms("ÉCOLE")

    assert result == "ecole"


def test_normalize_text_strict():
    result = normalize_text_strict("École!!! Test")

    assert result == "ecole test"


def test_detecter_mots_cles_true():
    result = detecter_mots_cles(
        "hello world",
        ["world"]
    )

    assert result is True


def test_detecter_mots_cles_false():
    result = detecter_mots_cles(
        "hello",
        ["xyz"]
    )

    assert result is False