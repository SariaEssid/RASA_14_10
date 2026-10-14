import logging
import re
log = logging.getLogger(__name__)

class VALID_QE:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    def is_valid_question(text: str) -> bool:
        """
        Returns True if the text looks like a legitimate question/sentence,
        and False if it contains excessive noise, gibberish, or mashed keys.
        """
        if not text or not text.strip():
            return False

        text = text.strip()

        # 1. Clean out common punctuation that doesn't count as noise
        # (keeps letters, numbers, spaces, and normal punctuation like ?, !, ., ', -)
        clean_text = re.sub(r"[?!.,'\-\s]", "", text)

        # 2. Extract remaining bad symbols (+, *, =, _, /, etc.)
        special_chars = re.findall(r"[^\w\s]", clean_text)

        # 3. Calculate noise ratio
        # If more than 20% of the non-space characters are weird symbols, it's noise.
        if len(clean_text) > 0:
            noise_ratio = len(special_chars) / len(clean_text)
            if noise_ratio > 0.20:
                return False

        # 4. Check for meaningless repetitive patterns (e.g., -+-.-0-00-00)
        if re.search(r"([-+.*0_]{4,})", text):
            return False

        # 5. Word lengths check (optional, flags typing blindly like 'asdfghjkl')
        words = text.split()
        # If the user typed something, but there are no actual letters anywhere
        if not any(c.isalpha() for c in text):
            return False

        return True

# --- Zone de Test ---
if __name__ == "__main__":
    # --- Test Cases ---
    test_cases = [
        "comment accé-+-.-0-00-00",  # Expected: False (too many symbols/patterns)
        "Comment accèder à mon compte ?",  # Expected: True
        "Bonjour! ++--++",  # Expected: False
        "Qu'est-ce que c'est ?",  # Expected: True
        "12345-67890",  # Expected: False (no alphabetic characters)
    ]

    for test in test_cases:
        print(f"'{test}' -> Valid? {VALID_QE.is_valid_question(test)}")