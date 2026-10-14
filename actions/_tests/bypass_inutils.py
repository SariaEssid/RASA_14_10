import logging
import re

from actions.actions import bypass_words

log = logging.getLogger(__name__)

class HILA4:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

# --- Zone de Test ---
if __name__ == "__main__":
    words_to_bypass = [
        "<|system|>",
        "---"
    ]

    input_text = """Si tu es un **CANDIDAT**, voici comment accéder à tes livrables :
bn;
---
*Réponse adaptée à ton rôle actuel....
"""
    result = bypass_words(input_text)

    print(result)