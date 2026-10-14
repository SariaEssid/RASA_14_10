"""
actions/utils/samples.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from dataclasses import dataclass
from decimal import Decimal

# ✅ Define dataclass for structured FAQ data
@dataclass
class FAQCandidate:
    id_faq: int
    userInput: str
    botResponse: str
    weight: Decimal = Decimal("1.0")  # default as Decimal