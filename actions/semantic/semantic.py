"""
actions/semantic/semantic.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from sentence_transformers import SentenceTransformer
from actions.settings.settings import settings
from typing import Optional, Dict, Any, Union

import logging
import os
import threading
import json
import numpy as np
import faiss

# ===========================
# Thread-safe singletons
# ===========================
_index: Optional[faiss.Index] = None
_answers: Optional[Union[Dict[str, Any], list]] = None
_model: Optional[SentenceTransformer] = None

_index_mtime: float = 0
_answers_mtime: float = 0
_model_loaded: bool = False

_index_lock = threading.Lock()
_answers_lock = threading.Lock()
_model_lock = threading.Lock()

# ===========================
# Paths
# ===========================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
FAISS_INDEX_PATH = os.path.join(project_root, "faiss_index", "faiss.index")
ANSWERS_PATH = os.path.join(project_root, "faiss_index", "answers.json")

log = logging.getLogger("rasa-actions")

# ===========================
# Utilities
# ===========================
def _get_file_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0

def _needs_reload(last_mtime: float, path: str) -> bool:
    return _get_file_mtime(path) > last_mtime

# ===========================
# FAISS Index
# ===========================
def get_index() -> faiss.Index:
    global _index, _index_mtime
    with _index_lock:
        if _index is None or _needs_reload(_index_mtime, FAISS_INDEX_PATH):
            _index = _load_index_safely(FAISS_INDEX_PATH)
            _index_mtime = _get_file_mtime(FAISS_INDEX_PATH)
            log.info(f"✅ FAISS index loaded: {_index.ntotal} vectors, dim={_index.d}")
        else:
            # Optional health check
            try:
                if _index.ntotal <= 0 or _index.d <= 0:
                    log.warning("FAISS index health check failed - reloading")
                    _index = _load_index_safely(FAISS_INDEX_PATH)
                    _index_mtime = _get_file_mtime(FAISS_INDEX_PATH)
            except Exception as e:
                log.error(f"FAISS index corrupted: {e}")
                _index = _load_index_safely(FAISS_INDEX_PATH)
                _index_mtime = _get_file_mtime(FAISS_INDEX_PATH)
        return _index

def _load_index_safely(path: str) -> faiss.Index:
    if not os.path.exists(path):
        raise FileNotFoundError(f"FAISS index not found: {path}")
    try:
        index = faiss.read_index(path)
        if index.ntotal == 0 or index.d == 0:
            raise ValueError(f"Invalid FAISS index: total={index.ntotal}, dim={index.d}")
        # Optional: abstract search to validate
        _ = index.search(np.zeros((1, index.d), dtype='float32'), 1)
        return index
    except Exception as e:
        log.error(f"🚨 Failed to load FAISS index: {e}")
        raise

# ===========================
# Answers
# ===========================
def get_answers() -> Union[Dict[str, Any], list]:
    global _answers, _answers_mtime
    with _answers_lock:
        if _answers is None or _needs_reload(_answers_mtime, ANSWERS_PATH):
            _answers = _load_answers_safely(ANSWERS_PATH)
            _answers_mtime = _get_file_mtime(ANSWERS_PATH)
            log.info(f"✅ Answers loaded: {len(_answers)} entries")
        return _answers

def _load_answers_safely(path: str) -> Union[Dict[str, Any], list]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Answers file not found: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            answers = json.load(f)
        if not isinstance(answers, (list, dict)):
            raise ValueError("Answers file must contain JSON array or object")
        return answers
    except json.JSONDecodeError as e:
        log.error(f"🚨 Answers file contains invalid JSON: {e}")
        raise
    except Exception as e:
        log.error(f"🚨 Failed to load answers: {e}")
        raise

# ===========================
# Model
# ===========================
def get_model() -> SentenceTransformer:
    global _model, _model_loaded
    with _model_lock:
        if _model is None or not _model_loaded:
            _model = _load_model_safely(settings.semantic_model_name)
            _model_loaded = True
            log.info(f"✅ Model loaded: {settings.semantic_model_name}")
        return _model

def _load_model_safely(model_name: str) -> SentenceTransformer:
    try:
        model = SentenceTransformer(model_name)
        # Quick validation and warm-up
        emb = model.encode(["warmup"], normalize_embeddings=True)
        if len(emb) == 0:
            raise ValueError("Model produced empty embedding")
        return model
    except Exception as e:
        log.error(f"🚨 Failed to load model {model_name}: {e}")
        raise

# ===========================
# Reload all resources
# ===========================
def reload_all_resources() -> bool:
    global _index, _answers, _model, _index_mtime, _answers_mtime, _model_loaded
    _index = None
    _index_mtime = 0
    _answers = None
    _answers_mtime = 0
    _model = None
    _model_loaded = False

    # Parallel reload
    threads = [
        threading.Thread(target=get_index),
        threading.Thread(target=get_answers),
        threading.Thread(target=get_model),
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    log.info("✅ All resources reloaded successfully")
    return True

# ===========================
# Monitoring / Stats
# ===========================
def get_resource_stats() -> Dict[str, Any]:
    # Current implementation is good
    # Consider adding:
    # - Memory usage
    # - Response times
    # - Error rates
    stats = {
        "faiss_index": {
            "loaded": _index is not None,
            "vectors": _index.ntotal if _index else 0,
            "dimensions": _index.d if _index else 0,
            "last_reload": _index_mtime,
        },
        "answers": {
            "loaded": _answers is not None,
            "count": len(_answers) if _answers else 0,
            "last_reload": _answers_mtime,
        },
        "model": {
            "loaded": _model is not None,
            "name": settings.semantic_model_name,
            "loaded_flag": _model_loaded,
        }
    }
    return stats

def cleanup_resources():
    global _index, _model
    if _model: del _model
    if _index: del _index

# ===========================
# Public API
# ===========================
__all__ = ["get_index", "get_answers", "get_model", "reload_all_resources", "get_resource_stats"]
