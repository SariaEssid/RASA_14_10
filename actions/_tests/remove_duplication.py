import logging
import re
log = logging.getLogger(__name__)

class HILA1:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    def remove_consecutive_duplicates(text):

        pattern = r'\b(\w+)\b(?:\s+\1\b)+'
        return re.sub(pattern, r'\1', text)

# --- Zone de Test ---
if __name__ == "__main__":
    input_text = "Enseignant Langue Langue Communication et Citoyenneté"
    result = HILA1.remove_consecutive_duplicates(input_text)

    log.info(result)