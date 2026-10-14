"""
tests/unit/test_action_buttons.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.actions import generate_composante_buttons

def test_buttons():
    b = generate_composante_buttons()
    assert isinstance(b, list)
    assert len(b) > 0