"""
actions/settings/config.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
from pathlib import Path

from dotenv import load_dotenv

import logging
import os

# Project root: chatbot_RASA/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env.dev"

# Load .env.dev before reading or validating environment variables
load_dotenv(dotenv_path=ENV_FILE, override=False)

log = logging.getLogger("rasa-actions")
LANG_CHAIN_URL = os.getenv("LANG_CHAIN_URL")
API_URL = os.getenv("API_URL")

# ✅ Add startup validation
class ConfigurationError(Exception):
    pass

def validate_environment():
    required_vars = [
        "API_URL",
        "ANONYMIZATION_SALT",
        "LANG_CHAIN_URL",
        "RASA_RAG_TOKEN",
        "JSON_PATH_FILES",
        "PDF_PATH_FILES",
        "MARKDOWN_PATH_FILES",
        "PHI3_PATH",
        "RAG_DEFAULT_CHUNKS",
        "EXPERT_TABLE_TOP_K",
        "RASA_TO_SPRING_TOKEN"
    ]

    missing = [
        name for name in required_vars
        if not (os.getenv(name) or "").strip()
    ]

    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {missing}"
        )

    integer_ranges = {
        "RAG_DEFAULT_CHUNKS": (1, 20),
        "EXPERT_TABLE_TOP_K": (1, 20),
    }

    for name, (minimum, maximum) in integer_ranges.items():
        raw_value = os.environ[name].strip()
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ConfigurationError(
                f"{name} must be an integer"
            ) from exc

        if not minimum <= value <= maximum:
            raise ConfigurationError(
                f"{name} must be between {minimum} and {maximum}"
            )

    log.info(f"Environment variables validated: {', '.join(required_vars)}")


# Run validation on import
validate_environment()
