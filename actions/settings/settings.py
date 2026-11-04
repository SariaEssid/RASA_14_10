
"""
actions/settings/settings.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from pathlib import Path
from typing import Optional

from pydantic import (
    AnyHttpUrl,
    BaseSettings,
    Field,
    SecretStr,
    validator,
    root_validator
)

from actions.settings.config import (
    PROJECT_ROOT,
    get_app_environment,
    get_env_file
)

import logging

log = logging.getLogger("rasa-actions")


class Settings(BaseSettings):

    # -------------------------
    # Environment
    # -------------------------

    APP_ENV: str = "production"

    # -------------------------
    # Project
    # -------------------------

    PROJECT_ROOT: Path = PROJECT_ROOT

    # -------------------------
    # Services / URLs
    # -------------------------

    API_URL: AnyHttpUrl
    LANG_CHAIN_URL: AnyHttpUrl

    # -------------------------
    # Secrets
    # -------------------------

    RASA_RAG_TOKEN: SecretStr
    RASA_TO_SPRING_TOKEN: SecretStr
    ANONYMIZATION_SALT: SecretStr

    # -------------------------
    # AI Forge
    # -------------------------

    MODEL_API_KEYS: Optional[str] = None
    LLM_BASE_URL: Optional[AnyHttpUrl] = None
    LLM_MODEL: Optional[str] = None

    # -------------------------
    # RAG
    # -------------------------

    RAG_DEFAULT_CHUNKS: int = Field(..., ge=1, le=20)
    EXPERT_TABLE_TOP_K: int = Field(..., ge=1, le=20)

    # -------------------------
    # General
    # -------------------------

    DRIVE_LINK: str = (
        "https://drive.google.com/uc?export=download&id"
    )

    SEMANTIC_THRESHOLD: float = 0.9
    FOLLOWUP_THRESHOLD: float = 0.55

    log_level: str = "INFO"

    # -------------------------
    # Circuit Breaker
    # -------------------------

    CIRCUIT_FAILURE_THRESHOLD: int = Field(5, ge=1, le=100)
    CIRCUIT_RECOVERY_TIMEOUT: int = Field(120, ge=1)

    # -------------------------
    # Performance
    # -------------------------

    MAX_USER_QUESTION_WORDS: int = Field(50, ge=1)
    MAX_CONNECTIONS: int = Field(200, ge=1)
    MAX_KEEPALIVE_CONNECTIONS: int = Field(50, ge=1)
    KEEPALIVE_EXPIRY: float = Field(30.0, gt=0)

    # -------------------------
    # Timeout
    # -------------------------

    TIMEOUT_CONNECT: float = Field(5.0, gt=0)
    TIMEOUT_READ: float = Field(10.0, gt=0)
    TIMEOUT_WRITE: float = Field(10.0, gt=0)
    TIMEOUT_POOL: float = Field(5.0, gt=0)

    # -------------------------
    # Network
    # -------------------------

    RETRY_NETWORK_FAILURES: int = Field(3, ge=1, le=5)
    MAX_REQUEST_ROLLING_RETRIES: int = Field(100, ge=1)

    # -------------------------
    # RAG Retry Policy
    # -------------------------

    RAG_MAX_ATTEMPTS: int = Field(2, ge=1, le=3)
    RAG_RETRY_DELAY_SECONDS: float = Field(0.5, ge=0)

    # -------------------------
    # File directories
    # -------------------------

    JSON_PATH_FILES: Path
    PDF_PATH_FILES: Path
    MARKDOWN_PATH_FILES: Path

    # -------------------------
    # Models
    # -------------------------

    semantic_model_name: str = "./models/semantic_model"

    HF_HUB_OFFLINE: bool = False

    ACTIVE_SESSION: str = "2025-2026"

    # -------------------------
    # Tokens / Cache
    # -------------------------

    FUSION_QUESTIONS: int = Field(100, ge=1)
    CACHE_TIMEOUT_SECONDS: int = Field(300, ge=1)

    # -------------------------
    # Chunks for RAG
    # -------------------------

    CHUNK_SIZE: int = Field(768, ge=1)
    CHUNK_OVERLAP: int = Field(128, ge=0)

    # -------------------------
    # Scoring parameters
    # -------------------------

    BASIC_THRESHOLD_VALUE: float = 0.5
    MAIN_BEGIN_KEYWORD: float = 0.6
    MAIN_PARAM_VALUE: float = 0.57
    FALLBACK_VALUE: float = 0.3

    # -------------------------
    # Threshold validation
    # -------------------------

    @validator(
        "SEMANTIC_THRESHOLD",
        "FOLLOWUP_THRESHOLD",
        "BASIC_THRESHOLD_VALUE",
        "MAIN_BEGIN_KEYWORD",
        "MAIN_PARAM_VALUE",
        "FALLBACK_VALUE"
    )
    def validate_threshold(cls, value):
        if not 0 <= value <= 1:
            raise ValueError(
                "Threshold must be between 0 and 1"
            )
        return value

    # -------------------------
    # URL validation
    # -------------------------

    @validator("API_URL", "LANG_CHAIN_URL")
    def validate_service_url(cls, value):
        if value.scheme not in ("http", "https"):
            raise ValueError("Service URL must use HTTP or HTTPS")
        return value

    # -------------------------
    # Token validation
    # -------------------------

    @validator(
        "RASA_RAG_TOKEN",
        "RASA_TO_SPRING_TOKEN",
        "ANONYMIZATION_SALT"
    )
    def validate_secret(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError("Secret configuration cannot be empty")
        return value

    # -------------------------
    # Cross-field validation
    # -------------------------

    @root_validator
    def validate_related_settings(cls, values):

        max_connections = values.get("MAX_CONNECTIONS")
        keepalive_connections = values.get(
            "MAX_KEEPALIVE_CONNECTIONS"
        )

        if (
            max_connections is not None
            and keepalive_connections is not None
            and keepalive_connections > max_connections
        ):
            raise ValueError(
                "MAX_KEEPALIVE_CONNECTIONS cannot exceed "
                "MAX_CONNECTIONS"
            )

        chunk_size = values.get("CHUNK_SIZE")
        chunk_overlap = values.get("CHUNK_OVERLAP")

        if (
            chunk_size is not None
            and chunk_overlap is not None
            and chunk_overlap >= chunk_size
        ):
            raise ValueError(
                "CHUNK_OVERLAP must be smaller than CHUNK_SIZE"
            )

        return values

    # -------------------------
    # File paths
    # -------------------------

    @property
    def SPECIALITIES_JSON_PATH(self) -> Path:
        return self.JSON_PATH_FILES / "needed_positions_by_speciality.json"

    @property
    def RESULTS_STAT_JSON_PATH(self) -> Path:
        return self.JSON_PATH_FILES / "statistiques_resultats_pg.json"

    @property
    def GRADES_JSON_PATH(self) -> Path:
        return self.JSON_PATH_FILES / "concerned_grades.json"

    @property
    def PATH_HIERARCHY_ALL(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy_all.pdf"

    @property
    def PATH_HIERARCHY(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy.pdf"

    @property
    def PATH_HIERARCHY_DATE(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy_date.pdf"

    @property
    def PATH_HIERARCHY_DURATION(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy_duration.pdf"

    @property
    def PATH_HIERARCHY_EXAM_KIND(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy_kind_exam.pdf"

    @property
    def PATH_HIERARCHY_PLACE(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy_place.pdf"

    @property
    def PATH_HIERARCHY_SCORE(self) -> Path:
        return self.PDF_PATH_FILES / "hierarchy_score.pdf"

    @property
    def PATH_HIERARCHY_EVALS_JURYS_MRKDN_BY(self) -> Path:
        return self.MARKDOWN_PATH_FILES / "hierarchy_evals_jurys_by.md"

    @property
    def PATH_HIERARCHY_EVALS_JURYS_MRKDN_NAME(self) -> Path:
        return self.MARKDOWN_PATH_FILES / "hierarchy_evals_jurys_name.md"

    @property
    def PATH_HIERARCHY_EVALS_JURYS_MRKDN_ALL(self) -> Path:
        return self.MARKDOWN_PATH_FILES / "hierarchy_evals_jurys_all.md"

    # -------------------------
    # Pydantic v1 configuration
    # -------------------------

    class Config:
        env_file = None
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# -------------------------
# Single settings instance
# -------------------------

settings = Settings(_env_file=get_env_file())

log.info(
    "Configuration successfully validated for environment: %s",
    settings.APP_ENV
)