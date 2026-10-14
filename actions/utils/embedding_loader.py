"""
actions/utils/embedding_loader.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from threading import Lock
from sentence_transformers import SentenceTransformer
from actions.settings.settings import settings

import os

_embedder = None
_lock = Lock()

def get_embedder() -> SentenceTransformer:
    """
    Lazily load the sentence-transformers embedder.

    Important: Do NOT call this at module import time elsewhere.
    Otherwise pods may block on model download during startup.
    """
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                model_id = getattr(settings, "semantic_model_name", "all-MiniLM-L6-v2")

                # Optional: allow forcing offline mode from env to prevent startup stalls.
                # (If the model isn't already cached, SentenceTransformer will raise.)
                if os.getenv("HF_HUB_OFFLINE") == "1" or os.getenv("TRANSFORMERS_OFFLINE") == "1":
                    os.environ.setdefault("HF_HUB_OFFLINE", "1")
                    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

                _embedder = SentenceTransformer(model_id)
    return _embedder
