import logging
import os
import re
from datetime import datetime, timezone

import requests

from actions.settings.config import API_URL

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logger = logging.getLogger("rasa-actions")

_SENSITIVE_KEYS = {"password", "passwd", "mdp", "pass", "jwt", "token", "authorization", "secret"}
_SECRET_IN_TEXT = re.compile(
    r"(?i)(\b(?:pass(?:word|wd)?|mdp|mot\s+de\s+passe)(?:\s*[=:]\s*|\s+(?:est|is)\s+))[^;\n]+"
)

def redact_secrets(text):
    """Replace anything after a password label with [REDACTED]."""
    return _SECRET_IN_TEXT.sub(r"\1[REDACTED]", text) if isinstance(text, str) else text

def sanitize_payload(obj):
    """Recursively drop sensitive keys (handles nested dicts and lists)."""
    if isinstance(obj, dict):
        return {k: sanitize_payload(v) for k, v in obj.items()
                if str(k).lower() not in _SENSITIVE_KEYS}
    if isinstance(obj, (list, tuple)):
        return [sanitize_payload(v) for v in obj]
    return obj


def configure_logger() -> None:
    """Configure the logger once without altering the root logger."""
    level = getattr(logging, LOG_LEVEL, logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)

    logger.setLevel(level)


configure_logger()

async def log_chat(
    user_id: str,
    session_id: str,
    user_input: str,
    bot_response: str,
    rasa_intent: str,
    confidence: float,
):
    try:
        dt = datetime.now(timezone.utc)
        user_input = redact_secrets(user_input)
        bot_response = redact_secrets(bot_response)

        logger.info("ℹ️ session_id : %s", session_id)

        payload = {
            "userId": user_id,
            "sessionId": session_id,
            "userInput": user_input,
            "botReply": bot_response,
            "rasaIntent": rasa_intent,
            "confidence": confidence,
            "messageExchangeDate": dt.isoformat(),
        }

        logger.warning(
            "# ⚠️ LOG-CHAT Saving: %s-%s-%s",
            rasa_intent,
            session_id,
            user_id,
        )
        response = requests.post(
            f"{API_URL}/logChat",
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.exception("🚨 Failed to log chat: %s", e)
        return False

def notify_team_leader_by_technical_problem(payload):
    payload = sanitize_payload(payload)
    try:
        response = requests.post(
            f"{API_URL}/notifyTeamLeaderByTechnicalProblem",
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.exception("🚨 Failed to log chat: %s", e)
        return False

def log_faiss_unknown_question(
    question: str,
    score: float,
    index: int,
    intent: str,
    user_id: str,
    session_id: str,
):
    try:
        payload = {
            "question": question,
            "score": float(score),
            "matchedFaqIndex": int(index),
            "predictedIntent": intent,
            "userId": user_id,
            "sessionId": session_id,
        }

        logger.info("ℹ️ PAYLOAD : %s", payload)
        response = requests.post(
            f"{API_URL}/logFaissUnknownQuestion",
            json=payload,
            timeout=5,
        )

        logger.info("# ℹ️ LOG-FAISS Saved : %s", intent)
        logger.warning(
            "Unknown question logged: Message='%s', Score=%.2f, Index=%s, Intent='%s', Session='%s'",
            question,
            score,
            index,
            intent,
            session_id,
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.exception("🚨 API log failed: %s", e)
        return False