"""
tests/unit/test_text_processing.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.actions import (
    remove_excluded_patterns,
    clean_llm_response
)

def test_remove_excluded_patterns():
    input_text = "Est-ce qu'il sera présent ?"
    result = remove_excluded_patterns(input_text)

    assert "il sera présent ?" in result

def test_clean_llm_response():
    dirty_text = "Détails.\n\n\nFin."
    result = clean_llm_response(dirty_text)

    assert "\n\n\n" not in result