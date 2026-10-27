"""
actions/settings/settings.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, validator
from actions.settings.config import API_URL

import logging
import os

log = logging.getLogger("rasa-actions")

JSON_FILES_DIR = Path(os.environ["JSON_PATH_FILES"].strip())
PDF_FILES_DIR = Path(os.environ["PDF_PATH_FILES"].strip())
MARKDOWN_FILES_DIR = Path(os.environ["MARKDOWN_PATH_FILES"].strip())

class Settings(BaseSettings):

    log.info(f"IMPORTANT TAG -> Loaded env constants under API_URL : {API_URL}")

    # -------------------------
    # Pydantic v1 config
    # -------------------------
    class Config:
        env_file = ".env.dev"
        extra = "ignore"
        # In v1, we usually specify case sensitivity here if needed
        case_sensitive = False

    # -------------------------
    # Project
    # -------------------------
    PROJECT_ROOT: str = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    # -------------------------
    # RASA-RAG Service
    # -------------------------
    RASA_RAG_TOKEN = os.getenv("RASA_RAG_TOKEN")
    RAG_DEFAULT_CHUNKS: int = os.getenv("RAG_DEFAULT_CHUNKS")
    EXPERT_TABLE_TOP_K: int = os.getenv("EXPERT_TABLE_TOP_K")
    RASA_TO_SPRING_TOKEN = os.getenv("RASA_TO_SPRING_TOKEN")

    # -------------------------
    # General
    # -------------------------
    DRIVE_LINK: str = "https://drive.google.com/uc?export=download&id"
    semantic_threshold: float = 0.9
    FOLLOWUP_THRESHOLD = 0.55
    log_level: str = "INFO"
    ANONYMIZATION_SALT: Optional[str] = os.getenv("ANONYMIZATION_SALT")

    # -------------------------
    # AI Forge
    # -------------------------
    MODEL_API_KEYS: Optional[str] = os.getenv("MODEL_API_KEYS")
    LLM_BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL")
    LLM_MODEL: Optional[str] = os.getenv("LLM_MODEL")

    # -------------------------
    # Circuit Breaker
    # -------------------------
    CIRCUIT_FAILURE_THRESHOLD: int = 5
    CIRCUIT_RECOVERY_TIMEOUT: int = 120

    # -------------------------
    # Performance
    # -------------------------
    MAX_USER_QUESTION_WORDS: int = 300
    MAX_CONNECTIONS: int = 200
    MAX_KEEPALIVE_CONNECTIONS: int = 50
    KEEPALIVE_EXPIRY: float = 30.0

    # -------------------------
    # Timeout
    # -------------------------
    TIMEOUT_CONNECT: float = 5.0
    TIMEOUT_READ: float = 10.0
    TIMEOUT_WRITE: float = 10.0
    TIMEOUT_POOL: float = 5.0

    # -------------------------
    # Network
    # -------------------------
    RETRY_NETWORK_FAILURES: int = 3
    MAX_REQUEST_ROLLING_RETRIES: int = 100

    # -------------------------
    # File Paths
    # -------------------------
    # Positions - Statistics - Grades
    SPECIALITIES_JSON_PATH: Optional[str] = str(JSON_FILES_DIR / "needed_positions_by_speciality.json")
    RESULTS_STAT_JSON_PATH: Optional[str] = str(JSON_FILES_DIR / "statistiques_resultats_pg.json")
    GRADES_JSON_PATH: Optional[str] = str(JSON_FILES_DIR / "concerned_grades.json")

    # Hierarchy
    PATH_HIERARCY_ALL: Optional[str] = str(PDF_FILES_DIR / "hierarchy_all.pdf")
    PATH_HIERARCY: Optional[str] = str(PDF_FILES_DIR / "hierarchy.pdf")
    PATH_HIERARCY_DATE: Optional[str] = str(PDF_FILES_DIR / "hierarchy_date.pdf")
    PATH_HIERARCY_DURATION: Optional[str] = str(PDF_FILES_DIR / "hierarchy_duration.pdf")
    PATH_HIERARCY_EXAM_KIND: Optional[str] = str(PDF_FILES_DIR / "hierarchy_kind_exam.pdf")
    PATH_HIERARCY_PLACE: Optional[str] = str(PDF_FILES_DIR / "hierarchy_place.pdf")
    PATH_HIERARCY_SCORE: Optional[str] = str(PDF_FILES_DIR / "hierarchy_score.pdf")

    # Experts
    PATH_HIERARCY_EVALS_JURYS_MRKDN_VS: Optional[str] = str(MARKDOWN_FILES_DIR / "hierarchy_evals_jurys_vs.md")
    PATH_HIERARCY_EVALS_JURYS_MRKDN_BY: Optional[str] = str(MARKDOWN_FILES_DIR / "hierarchy_evals_jurys_by.md")
    PATH_HIERARCY_EVALS_JURYS_MRKDN_NAME: Optional[str] = str(MARKDOWN_FILES_DIR / "hierarchy_evals_jurys_name.md")
    PATH_HIERARCY_EVALS_JURYS_MRKDN_ALL: Optional[str] = str(MARKDOWN_FILES_DIR / "hierarchy_evals_jurys_all.md")

    # -------------------------
    # Models
    # -------------------------

    # semantic_model_name: str = "all-MiniLM-L6-v2"  # BEFORE
    semantic_model_name = "./models/semantic_model"  # AFTER
    HF_HUB_OFFLINE: int = os.getenv("HF_HUB_OFFLINE") == "1"

    PHI_MODEL_PATH: str = os.getenv("PHI3_PATH")
    LLM_PHI3_API_URL: str = "http://localhost:8000/generate"

    ACTIVE_SESSION: str = "2025-2026"

    # -------------------------
    # Tokens
    # -------------------------
    FUSION_QUESTIONS: int = 100
    CACHE_TIMEOUT_SECONDS: int = 300

    # -------------------------
    # Chunks for RAG
    # -------------------------
    CHUNK_SIZE = 768  # Réduit la taille pour de meilleurs "hits" sur les paires clé/valeur
    CHUNK_OVERLAP = 128

    # -------------------------
    # Validators
    # -------------------------
    @validator("semantic_threshold")
    def validate_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        return v


settings = Settings()
