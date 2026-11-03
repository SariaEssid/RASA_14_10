"""
core/nlp.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import spacy
from threading import Lock

_nlp = None
_nlp_lock = Lock()


def get_nlp():
    global _nlp

    if _nlp is None:
        with _nlp_lock:
            if _nlp is None:
                try:
                    _nlp = spacy.load("fr_core_news_sm")
                except OSError as exc:
                    raise RuntimeError(
                        "Veuillez installer le modèle français : "
                        "python -m spacy download fr_core_news_sm"
                    ) from exc

    return _nlp