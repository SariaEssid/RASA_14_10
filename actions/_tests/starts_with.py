import logging
log = logging.getLogger(__name__)

class BEGIN_WITH:
    """
    actions/_tests/starts_with.py
    """

    START_WORDS = (
        "et", "et pour", "et puis", "et concernant",
        "non", "oui", "donc", "meme", "même", "alors", "aucun", "pas"
    )

    @classmethod
    def starts_with_discourse_marker(cls, question: str) -> bool:
        """
        Checks if the given question starts with any of the defined discourse markers.
        Handles leading/trailing whitespaces and case-insensitivity.
        """
        if not question:
            return False

        # Clean the text: remove surrounding whitespace and convert to lowercase
        cleaned_question = question.strip().lower()

        return cleaned_question.startswith(cls.START_WORDS)

# --- Zone de Test ---
if __name__ == "__main__":
    # Test cases
    test_questions = [
        "Et pour le projet, qu'en est-il ?",
        "Alors, on commence quand ?",
        "Même si c'est difficile, tu viens ?",
        "Quel est votre nom ?",  # False
        "   non je ne pense pas "  # True (handles spaces)
    ]

    for q in test_questions:
        result = BEGIN_WITH.starts_with_discourse_marker(q)
        print(f"'{q.strip()}' -> {result}")