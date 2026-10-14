"""
tests/unit/test_models.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.utils.models import FAQCandidate
from decimal import Decimal

def test_faq_model():
    f = FAQCandidate(1, "in", "out", Decimal("1.0"))
    assert f.weight == Decimal("1.0")