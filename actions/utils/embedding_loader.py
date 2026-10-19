"""
actions/utils/embedding_loader.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import logging
import os
import threading
from pathlib import Path
from threading import Lock

from sentence_transformers import SentenceTransformer
from actions.settings.settings import settings

log = logging.getLogger("rasa-actions")

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_embedder = None
_lock = Lock()


def _resolve_model_id() -> tuple[str, bool]:
    """Return (model id or absolute path, is_local)."""
    raw = getattr(settings, "semantic_model_name", DEFAULT_MODEL)
    path = Path(raw)
    if raw.startswith((".", "/")) or path.exists():
        path = path if path.is_absolute() else (Path.cwd() / path)
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(
                f"Embedding model folder not found: {path}. "
                "Copy it into the image or set SEMANTIC_MODEL_NAME to a hub id."
            )
        return str(path), True
    return raw, False


def get_embedder() -> SentenceTransformer:
    """Lazily load the embedder. Never call at import time."""
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                model_id, is_local = _resolve_model_id()
                offline = os.getenv("HF_HUB_OFFLINE") == "1"
                _embedder = SentenceTransformer(
                    model_id,
                    device="cpu",
                    local_files_only=is_local or offline,
                )
    return _embedder


def warm_up_async() -> None:
    """Call once at server startup so the first request is not slow."""
    threading.Thread(target=get_embedder, daemon=True).start()