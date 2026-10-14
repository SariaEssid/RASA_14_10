"""
actions/answer_from_file/answer_from_markdown/experts_rag/action_llm_markdown.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations
from pathlib import Path
import os

def get_markdown_content(path: Path | None = None) -> str:
    """
    Always reads markdown directly from file (NO CACHE).
    """
    path = str(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Markdown file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return f.read()