import logging
import os
from datetime import datetime, timezone

import httpx

from actions.settings.config import API_URL

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logger = logging.getLogger("rasa-actions")

_client = None

def _get_client() -> httpx.AsyncClient:
    """Create lazily, inside the running event loop (not at import time)."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=5.0)
    return _client

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
        "userInput": user_input,
        "botReply": bot_response,
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

    return await post_to_backend("aichatbot/logChat", payload)

async def post_to_backend(endpoint: str, payload: dict) -> bool:
    try:
        response = await _get_client().post(f"{API_URL}{endpoint}", json=payload)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        logger.error("Backend %s returned HTTP %s", endpoint, e.response.status_code)
    except httpx.RequestError as e:
        logger.error("Backend %s unreachable: %s", endpoint, e)
    except httpx.HTTPError as e:
        logger.error("Erreur HTTP inattendue sur %s: %s", endpoint, e)
    return False

async def notify_team_leader_by_technical_problem(payload):
    return await post_to_backend("aichatbot/notifyTeamLeaderByTechnicalProblem", payload)

async def log_faiss_unknown_question(
    question: str,
    score: float,
    index: int,
    intent: str,
    user_id: str,
    session_id: str,
):
    payload = {
        "question": question,
        "score": float(score),
        "matchedFaqIndex": int(index),
        "predictedIntent": intent,
        "userId": user_id,
        "sessionId": session_id,
    }
    return await post_to_backend("aichatbot/logFaissUnknownQuestion", payload)