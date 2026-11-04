"""
actions/settings/config.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import os
from pathlib import Path
from typing import Optional

# Project root: chatbot_RASA/
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_app_environment() -> str:
    """
    Determine the deployment environment.

    Default to production so that development configuration
    is never loaded accidentally.
    """
    return os.getenv("APP_ENV", "production").strip().lower()


def get_env_file() -> Optional[Path]:
    """
    Load .env.dev only in development.
    Production and other environments use system environment variables.
    """
    environment = get_app_environment()

    if environment == "development":
        return PROJECT_ROOT / ".env.dev"

    return None