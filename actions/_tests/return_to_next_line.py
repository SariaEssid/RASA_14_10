"""
actions/_tests/return_to_next_line.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import re
import logging
log = logging.getLogger(__name__)

class TextFormatter:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    def clean_response(text):
        # garder toutes les phrases complètes
        last_dot = text.rfind(".")
        if last_dot != -1:
            return text[: last_dot + 1]
        return text

    @staticmethod
    def format_response(text: str) -> str:

        if not text:
            return ""

        text = text.strip()

        # corriger si la phrase est coupée
        if not text.endswith('.'):
            text = TextFormatter.clean_response(text)

        # découper les phrases
        sentences = re.split(r'\.(?=\s|$)', text)

        cleaned_sentences = [s.strip() for s in sentences if s.strip()]

        return ".\n".join(cleaned_sentences) + "."


# --- Zone de Test ---
if __name__ == "__main__":
    formatter = TextFormatter()

    test_cases = [
        "1.Le nombre de candidats participant au poste de Génie Civil pour la session 2025-2026 est de 100. Pour 2024-2025, le nombre e",
        "2.Le nombre de candidats participant au poste de Génie Civil pour la session 2025-2026 est de 100. Cela montre que la tendance de recrutement pour cette Spécialité.",
        "3.Le nombre de candidats participant au poste de Génie Civil pour la session 2025-2026 est de 100. Cela montre que la tendance de recrutement pour cette Spécialité. La section 3.2 est trés importante"
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"--- Example {i} ---")
        print(formatter.format_response(case))