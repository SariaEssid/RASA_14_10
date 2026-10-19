import logging
import os
import re
from datetime import datetime, timezone

import httpx

from actions.settings.config import API_URL

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logger = logging.getLogger("rasa-actions")

_SENSITIVE_KEYS = {"password", "passwd", "mdp", "pass", "jwt", "token", "authorization", "secret"}
_SECRET_IN_TEXT = re.compile(
    r"(?i)(\b(?:pass(?:word|wd)?|mdp|mot\s+de\s+passe)(?:\s*[=:]\s*|\s+(?:est|is)\s+))[^;\n]+"
)

_client = None

def _get_client() -> httpx.AsyncClient:
    """Create lazily, inside the running event loop (not at import time)."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=5.0)
    return _client

def redact_secrets(text):
    """Replace anything after a password label with [REDACTED]."""
    return _SECRET_IN_TEXT.sub(r"\1[REDACTED]", text) if isinstance(text, str) else text

def sanitize_payload(obj):
    """Recursively drop sensitive keys and redact secrets inside strings."""
    if isinstance(obj, dict):
        return {k: sanitize_payload(v) for k, v in obj.items()
                if str(k).lower() not in _SENSITIVE_KEYS}
    if isinstance(obj, (list, tuple)):
        return [sanitize_payload(v) for v in obj]
    if isinstance(obj, str):
        return redact_secrets(obj)
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

    logger.info("ℹ️ session_id : %s", session_id)

    payload = {
        "userId": user_id,
        "sessionId": session_id,
        "userInput": redact_secrets(user_input),
        "botReply": redact_secrets(bot_response),
        "rasaIntent": rasa_intent,
        "confidence": confidence,
        "messageExchangeDate": datetime.now(timezone.utc).isoformat(),
    }

    logger.warning(
        "# ⚠️ LOG-CHAT Saving: %s-%s-%s",
        rasa_intent,
        session_id,
        user_id
    )

    return await post_to_backend("logChat", payload)

async def post_to_backend(endpoint: str, payload: dict) -> bool:
    try:
        response = await _get_client().post(f"{API_URL}/{endpoint}", json=payload)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        logger.error("Backend %s returned HTTP %s", endpoint, e.response.status_code)
    except httpx.RequestError as e:
        logger.error("Backend %s unreachable: %s", endpoint, e)
    except Exception:
        logger.exception("Unexpected error calling %s", endpoint)
    return False

async def notify_team_leader_by_technical_problem(payload):
    payload = sanitize_payload(payload)
    return await post_to_backend("notifyTeamLeaderByTechnicalProblem", payload)

async def log_faiss_unknown_question(
    question: str,
    score: float,
    index: int,
    intent: str,
    user_id: str,
    session_id: str,
):
    payload = {
        "question": redact_secrets(question),
        "score": float(score),
        "matchedFaqIndex": int(index),
        "predictedIntent": intent,
        "userId": user_id,
        "sessionId": session_id,
    }
    return await post_to_backend("logFaissUnknownQuestion", payload)