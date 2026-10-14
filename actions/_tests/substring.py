import logging
log = logging.getLogger(__name__)

class HILA3:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    def is_followup_spacy(text):
        return text.split("**")[0].strip()

# --- Zone de Test ---
if __name__ == "__main__":
    input_text = "comment **pour Robot ChatBot.**"
    result = HILA3.is_followup_spacy(input_text)

    log.info(result)