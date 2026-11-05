"""
actions/answer_from_file/common_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx

from actions.constants.ActiveIntents import ActiveIntents
from actions.logging.logging_helpers import log_info_text
from actions.settings.settings import settings
from actions.utils.message_helpers import send_standard_fallback_problem_to_team_leader

LANG_CHAIN_URL = str(settings.LANG_CHAIN_URL)
class HttpClientManager:

    _client: httpx.AsyncClient | None = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:

        if cls._client is None or cls._client.is_closed:

            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=5.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0)
            )

        return cls._client

    @classmethod
    async def close(cls):

        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()

        cls._client = None


class RAGServiceUnavailable(Exception):
    """RAG service cannot be reached or is temporarily unavailable."""


class RAGAuthenticationError(Exception):
    """RAG service authentication/configuration failure."""


class RAGInvalidRequestError(Exception):
    """RAG rejected the request."""


class RAGUnexpectedResponseError(Exception):
    """RAG returned an unexpected response."""

##### Retrieve context from LangChain
def get_payload_rasa_rag_service():
    return {
        "userId": None,
        "sessionId": None,
        "userInput": None,
        "rasaIntent": str(ActiveIntents.NLU_FALLBACK.value),
        "confidence": 1,
        "messageExchangeDate": datetime.now(timezone.utc).isoformat()
    }

# rag_payload : used Exception metadata for unanswered questions and future analysis
rag_payload = get_payload_rasa_rag_service()

async def get_context_from_langchain_rag(
    action_label,
    native_question,
    domains,
    grades,
    nbr_chunks
):
    url = LANG_CHAIN_URL.rstrip("/") + "/rag/context"

    # payload : used for RAG request containing the question and retrieval filters
    payload = {
        "question": native_question,
        "domains": domains,
        "grades": grades,
        "nbr_chunks": nbr_chunks
    }

    max_attempts = 2
    retryable_statuses = {429, 502, 503, 504}

    # Reuse the shared asynchronous HTTP client.
    client = HttpClientManager.get_client()

    for attempt in range(max_attempts):

        try:
            response = await client.post(
                url,
                headers={
                    "X-Service-Token": settings.RASA_RAG_TOKEN.get_secret_value()
                },
                json=payload
            )

        except httpx.TransportError as exc:

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)
                continue

            bot_reply = f"RAG service connection or timeout failure : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, payload, bot_reply
            )
            raise RAGServiceUnavailable(bot_reply) from exc

        status = response.status_code

        # 1. No relevant context: not a technical failure
        if status == 404:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {}

            error_code = (
                error_data.get("code")
                or error_data.get("detail")
            )

            if error_code == "no_relevant_context":
                return "unknown", ""

            bot_reply = f"RAG endpoint returned an unexpected 404 : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, rag_payload, bot_reply
            )
            raise RAGUnexpectedResponseError(bot_reply)

        # 2. Authentication/configuration failure
        if status == 401:
            bot_reply = f"RAG authentication failed : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, rag_payload, bot_reply
            )
            raise RAGAuthenticationError(bot_reply)

        # 3. Invalid request
        if status == 422:
            bot_reply = f"RAG rejected the request (422) : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, rag_payload, bot_reply
            )
            raise RAGInvalidRequestError(bot_reply)

        # 4. Retry only selected transient HTTP errors
        if status in retryable_statuses:

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue

            bot_reply = f"RAG temporarily unavailable (HTTP {status}) : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, rag_payload, bot_reply
            )
            raise RAGServiceUnavailable(bot_reply)

        # 5. Other server errors
        if status >= 500:
            bot_reply = f"RAG service failure (HTTP {status}) : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, rag_payload, bot_reply
            )
            raise RAGServiceUnavailable(bot_reply)

        # 6. Unexpected client errors
        if status != 200:
            bot_reply = f"Unexpected RAG HTTP status: {status} : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(
                action_label, rag_payload, bot_reply
            )
            raise RAGUnexpectedResponseError(bot_reply)

        # 7. Successful response
        try:
            data = response.json()

        except ValueError as exc:
            bot_reply = f"RAG returned invalid JSON : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(action_label, rag_payload, bot_reply)
            raise RAGUnexpectedResponseError(bot_reply) from exc

        # Validate JSON structure
        if not isinstance(data, dict):
            bot_reply = f"RAG response must be a JSON object : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(action_label, rag_payload, bot_reply)
            raise RAGUnexpectedResponseError(bot_reply)

        context = data.get("context", "")
        filename = data.get("source_file", "unknown")

        # Validate context
        if not isinstance(context, str):
            bot_reply = f"Invalid RAG context format : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(action_label, rag_payload, bot_reply)
            raise RAGUnexpectedResponseError(bot_reply)

        # Validate source file
        if not isinstance(filename, str):
            bot_reply = f"Invalid RAG source_file format : {json.dumps(payload)}"
            await send_standard_fallback_problem_to_team_leader(action_label, rag_payload, bot_reply)
            raise RAGUnexpectedResponseError(bot_reply)

        log_info_text(action_label, f"domains : {domains}")
        log_info_text(action_label, f"grades : {grades}")
        log_info_text(action_label, f"filename : {filename}")
        log_info_text(action_label, f"nbr_chunks : {nbr_chunks}")

        return filename, context

    raise RAGServiceUnavailable("RAG request failed.")

def is_no_context_response(response: httpx.Response) -> bool:
    """True only for the RAG service's explicit 'nothing relevant found' 404."""
    if response.status_code != 404:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    # Checking `detail` avoids hiding a real 404 (wrong URL, wrong route).
    return isinstance(body, dict) and body.get("detail") == "no_relevant_context"