"""
actions/answer_from_file/tests/unit/test_answer_from_file_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import json

from actions.answer_from_file.answer_from_file_actions import (
    clean_query,
    JsonCacheManager,
    LLMCache,
    load_json_cached,
    extract_last_assistant
)

# =========================================================
# JsonCacheManager
# =========================================================

def test_json_cache_manager_set_get():
    JsonCacheManager.set("k1", {"a": 1})
    result = JsonCacheManager.get("k1")

    assert result == {"a": 1}


def test_json_cache_manager_invalidate():
    JsonCacheManager.set("k2", {"b": 2})
    JsonCacheManager.invalidate("k2")

    assert JsonCacheManager.get("k2") is None

# =========================================================
# LLMCache
# =========================================================

def test_llm_cache_set_get():
    LLMCache.set("Hello", "Answer")
    assert LLMCache.get("hello") == "Answer"  # case insensitive


# =========================================================
# load_json_cached
# =========================================================

def test_load_json_cached(monkeypatch, tmp_path):
    file = tmp_path / "data.json"
    file.write_text(json.dumps({"x": 1}))

    result = load_json_cached("cache1", file)

    assert result["x"] == 1


def test_load_json_cached_missing_file(monkeypatch, tmp_path):
    file = tmp_path / "missing.json"

    result = load_json_cached("cache2", file)

    assert result == {}


# =========================================================
# extract_last_assistant
# =========================================================

def test_extract_last_assistant():
    text = "A<|assistant|>FINAL ANSWER"
    result = extract_last_assistant(text)

    assert "FINAL ANSWER" in result


# =========================================================
# load_util_values
# =========================================================

class FakeTracker:
    def __init__(self):
        self.latest_message = {"text": "bonjour c'est quoi test"}

