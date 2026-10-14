import logging
import os
from datetime import datetime, timezone

import requests

from actions.settings.config import API_URL

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logger = logging.getLogger("rasa-actions")


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