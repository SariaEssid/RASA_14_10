"""
actions/answer_from_file/answer_from_file_actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from threading import Lock
from typing import Dict, Any
from typing import Optional
from typing import cast

import httpx
from cachetools import TTLCache
from openai import APITimeoutError, APIConnectionError, RateLimitError, AsyncOpenAI, APIStatusError
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam)
from rasa_sdk import Action

from actions.actions import get_payload
from actions.answer_from_file.bot_missions import fusion_question
from actions.constants.ActionsLabel import ActionsLabel
from actions.constants.Constants import BOT_MESSAGES, DIRECT_HAND_FLAG, DIRECT_HAND_LONG, GO_DETAILS
from actions.logging.logging_helpers import log_info_text, log_error_text, get_util_minimal_values_with_log, \
    log_exception_text, get_last_conversation
from actions.settings.settings import settings
from actions.utils.exception_error_messages import exception_fallback_err_dsi, exception_llm_err, exception_llm_err_dsi, \
    exception_fallback_err
from actions.utils.message_helpers import send_random_message_user_and_dsi
from actions.utils.slots_helpers import get_conversational_slots

# 🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩🚩
STOP_WORDS = ["svp", "stp", "please", "bonjour", "salut"]

"""
Production-ready, clean architecture for hybrid Rasa actions using an on-prem LLM.
- Centralized JSON cache manager (thread-safe)
- Centralized LLM response cache
- Base async action with httpx AsyncClient
- Concrete actions implement only prompt/data extraction
"""

# -----------------------------
# Centralized Cache Manager
# -----------------------------
class JsonCacheManager:
    """Thread-safe in-memory JSON cache manager with multiple namespaces."""
    _lock = Lock()
    _data: Dict[str, Any] = {}
    _time: Dict[str, float] = {}
    _timeout = settings.CACHE_TIMEOUT_SECONDS

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        with cls._lock:
            ts = cls._time.get(key)
            if ts is None:
                return None
            if (time.time() - ts) < cls._timeout:
                return cls._data.get(key)
            # expired
            cls._data.pop(key, None)
            cls._time.pop(key, None)
            return None

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        with cls._lock:
            cls._data[key] = value
            cls._time[key] = time.time()

    @classmethod
    def invalidate(cls, key: str) -> None:
        with cls._lock:
            cls._data.pop(key, None)
            cls._time.pop(key, None)


# ------------------------------
# Centralized LLM Response Cache
# ------------------------------
class LLMCache:
    """Thread-safe, bounded, context-aware LLM response cache."""

    _cache = TTLCache(maxsize=1000, ttl=3600)
    _lock = Lock()

    @classmethod
    def _generate_key(
        cls,
        query: str,
        model: str,
        system_mission: str,
        user_context: Optional[str] = None
    ) -> str:

        cache_data = {
            "query": (query or "").strip(),
            "model": model,
            "system_mission": (system_mission or "").strip(),
            "user_context": user_context or ""
        }

        serialized = json.dumps(
            cache_data,
            sort_keys=True,
            ensure_ascii=False
        )

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def get(
        cls,
        query: str,
        model: str,
        system_mission: str,
        user_context: Optional[str] = None
    ) -> Optional[str]:

        key = cls._generate_key(
            query, model, system_mission, user_context
        )

        with cls._lock:
            return cls._cache.get(key)

    @classmethod
    def set(
        cls,
        query: str,
        answer: str,
        model: str,
        system_mission: str,
        user_context: Optional[str] = None
    ) -> None:

        key = cls._generate_key(
            query, model, system_mission, user_context
        )

        with cls._lock:
            cls._cache[key] = answer

# -----------------------------
# Base Dynamic Action
# -----------------------------
def load_json_cached(cache_key: str, path: Path) -> dict:
    """Load JSON using centralized cache manager."""
    data = JsonCacheManager.get(cache_key)
    if data is not None:
        return data
    try:
        if not path.exists():
            log_error_text("LOAD JSON CACHED", f"File not found: {path}")
            return {}
        with path.open("r", encoding="utf-8") as utf_json:
            data = json.load(utf_json)
        JsonCacheManager.set(cache_key, data)
        return data
    except Exception as e:
        log_exception_text("LOAD JSON CACHED", f"Error loading JSON file {e}")
        return {}

def get_my_messages(
    system_message: str,
    prompt: str,
) -> list[ChatCompletionMessageParam]:
    messages: list[ChatCompletionMessageParam] = [
        cast(
            ChatCompletionSystemMessageParam,
            {"role": "system", "content": system_message},
        ),
        cast(
            ChatCompletionUserMessageParam,
            {"role": "user", "content": prompt},
        ),
    ]
    return messages

class BaseDynamicLLMAction(Action):
    """Base action providing async LLM calling, caching and helper utilities."""

    def __init__(self):

        self.api_key = settings.MODEL_API_KEYS

        if not self.api_key:
            raise ValueError("AI Forge API key is missing.")

        # OpenRouter OpenAI-compatible endpoint
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.LLM_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=5.0),
            max_retries=1
        )
    action_label = ActionsLabel.PY_BASE_LLM_ACTION.value

    async def ask(
            self,
            system_mission: str,
            prompt: str,
            model: str = settings.LLM_MODEL
    ) -> str:
        """
        Send prompt to OpenRouter DeepSeek model and return response.
        """

        response = await self.client.chat.completions.create(
                model=model,
                messages=get_my_messages(system_mission, prompt),
                stream=False,
            )

        return response.choices[0].message.content or ""

    async def call_custom_llm(
            self,
            action_label: str,
            prompt: str,
            payload_tech_error: dict,
            use_cache: bool = True,
    ) -> str:
        if use_cache:
            cached = LLMCache.get(
                query=prompt,
                model=settings.LLM_MODEL,
                system_mission=agent_mission
            )

            if isinstance(cached, str) and cached.strip():
                return cached

        try:
            answer = await self.ask(agent_mission, prompt)

            if not answer.strip():
                raise ValueError("LLM returned empty content")


        except APITimeoutError:
            return BOT_MESSAGES.get("huge_llm_response_time", "The response took too long.")


        # Handle 429 before APIStatusError because RateLimitError
        # is a more specific status error.
        except RateLimitError:
            return BOT_MESSAGES.get("free_tokens_reached", "The model is temporarily unavailable.")


        except APIStatusError as exc:

            if exc.status_code == 402:
                # OpenRouter uses 402 when the account has insufficient credits.
                return BOT_MESSAGES.get("free_tokens_reached", "The model is temporarily unavailable.")

            if exc.status_code == 408:
                return BOT_MESSAGES.get("huge_llm_response_time", "The response took too long.")

            if exc.status_code >= 500:
                return BOT_MESSAGES.get("error_model_connexion", "The model service is temporarily unavailable.")

            # Includes errors such as 401, 403, and 404. Keep provider details
            # out of the user-facing response.

            return BOT_MESSAGES.get("model_call_error", "I couldn't generate a response.")


        except APIConnectionError as exc:
            return await asyncio.to_thread(
                send_random_message_user_and_dsi,
                action_label,
                payload_tech_error,
                exc,
            )

        if use_cache:
            LLMCache.set(
                query=prompt,
                answer=answer,
                model=settings.LLM_MODEL,
                system_mission=agent_mission
            )

        return answer

    async def call_llm_safe(
            self,
            dispatcher,
            prompt: str,
            action_label: str,
            payload_tech_error: dict,
            retry: int = 1
    ) -> str:
        """
        Centralized LLM call with retry + logging + fallback handling
        """

        try:
            return await self.call_custom_llm(action_label, prompt, payload_tech_error)

        except TimeoutError as t_err:
            log_error_text("⏳ LLM Timeout:", str(t_err))

            if retry > 0:
                log_info_text("⚠️ Retrying with fallback LLM…", "")
                try:
                    return await self.call_custom_llm(action_label, prompt, payload_tech_error)
                except Exception as fallback_err:
                    answer = exception_fallback_err(dispatcher)
                    await exception_fallback_err_dsi(
                        dispatcher,
                        action_label,
                        payload_tech_error,
                        str(fallback_err)
                    )
                    raise RuntimeError(answer)

            raise

        except Exception as llm_err:
            answer = exception_llm_err(dispatcher)
            await exception_llm_err_dsi(
                dispatcher,
                action_label,
                payload_tech_error,
                str(llm_err)
            )
            raise RuntimeError(answer)

def load_util_values(tracker, action_label):

    user_id, session_id, confidence, intent = get_util_minimal_values_with_log(tracker, action_label)
    start_time = time.time()
    question_v0 = tracker.latest_message.get("text", "").strip()
    question = clean_query(question_v0)

    last_second_question = get_conversational_slots(tracker)
    payload_tech_error = get_payload(user_id, session_id, question, intent, confidence)

    return action_label, start_time, question, last_second_question, payload_tech_error, user_id, session_id, confidence, intent

def clean_query(text):
    text = text.lower()
    for w in STOP_WORDS:
        text = text.replace(w, "")
    return text.strip()

agent_mission = """
<|system|>
Tu es un ROBOT assistant expert, rigoureux et sympa chargé d'assiter les candidats Enseignants durant leurs Passages de grades (Enseignant Formateur (EF), Enseignant de Langue Communication et Citoyenneté (ELCC)) via le système de passage de grade ```PGPG```.       
- Ne jamais confondre : y a pas de ÉLÈVE -> CANDIDAT = ENSEIGNANT
"""

async def fusion_and_call_llm(
        self,
        dispatcher,
        last_last_user_question: str,
        question: str,
        action_label: str,
        payload_tech_error: dict,
        native_question_log: str
) -> str:
    """Helper to fuse questions, call the LLM safely, and log the process."""
    log_info_text("LASTA - 4 : ", native_question_log)

    prompt_qe = fusion_question(last_last_user_question, question)
    log_info_text(action_label + "FUSIONNED QUESTIONS : ", prompt_qe)

    native_question = await self.call_llm_safe(
        dispatcher=dispatcher,
        prompt=prompt_qe,
        action_label=action_label,
        payload_tech_error=payload_tech_error
    )

    log_info_text(f"{DIRECT_HAND_FLAG}", f" {action_label} - NATIVE QUESTION FUSIONNED : {native_question}")
    return native_question


def track_values(tracker, action_label, last_intent, last_second_question, intent):

    log_info_text(f"{DIRECT_HAND_LONG}", f"{GO_DETAILS}")

    maintained_intent = last_intent
    last_last_user_question, last_answer = get_last_conversation(tracker, action_label)

    log_info_text("LASTA- 0.1 : ", last_intent)
    log_info_text("LASTA- 0.2 : ", maintained_intent)
    log_info_text("LASTA- 1 : ", last_second_question)
    log_info_text("LASTA- 2 : ", last_last_user_question)
    log_info_text("LASTA- 3 : ", last_answer)

    if last_intent:
        log_info_text("HILA- 1 : ", intent + " - " + last_intent)

    return maintained_intent, last_last_user_question, last_answer

def log_params(action_label, domains, intent):

    log_info_text(action_label, "DOMAIN : " + str(domains))
    log_info_text(action_label, "INTENT : " + intent)