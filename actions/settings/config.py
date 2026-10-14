"""
actions/settings/config.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from dotenv import load_dotenv

import logging
import os

load_dotenv(override=True)
log = logging.getLogger("rasa-actions")
LANG_CHAIN_URL = os.getenv("LANG_CHAIN_URL")
API_URL = os.getenv("API_URL")

# ✅ Add startup validation
class ConfigurationError(Exception):
    pass

def validate_environment():
    required_vars = ['API_URL', 'ANONYMIZATION_SALT', 'LANG_CHAIN_URL']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ConfigurationError(f"Missing required environment variables: {missing}")
    log.info(f"Environment variables validated: {', '.join(required_vars)}")

# Run validation on import
validate_environment()