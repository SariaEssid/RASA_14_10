"""
actions/utils/test_services.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from collections import deque
from typing import List, Dict, Any
from aiocircuitbreaker import circuit
from actions.settings.config import API_URL
from actions.settings.settings import settings
from actions.utils.interfaces import IResultsService

import logging
import time
import httpx

log = logging.getLogger("rasa-actions")
# ---------------------------
# Circuit breaker configuration
# ---------------------------
# failure_threshold=5 -> circuit opens after 5 consecutive failures
# recovery_timeout=30 -> circuit stays open for 30 seconds before trying again
# expected_exception=httpx.HTTPError -> only counts HTTP/network errors
CIRCUIT = circuit(
    failure_threshold=settings.CIRCUIT_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_RECOVERY_TIMEOUT,
    expected_exception=httpx.HTTPError
)

# ---------------------------
# Helper to add Authorization header
# ---------------------------
def _auth_headers(token: str) -> dict:
    """Build Authorization header if token is provided."""
    return {"Authorization": f"Bearer {token}"} if token else {}

def get_start_time() -> float:
    return time.time()

# ---------------------------
# Service implementation
# ---------------------------

api_base_url = f"{API_URL.rstrip('/')}/"


async def log_request(request: httpx.Request) -> None:
    log.info("Outgoing request URL: %s", request.url)

class HttpResultsService(IResultsService):
    def __init__(self):
        # 1. Store the limits in a dedicated attribute
        self.pool_limits = httpx.Limits(
            max_connections=settings.MAX_CONNECTIONS,
            max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=settings.KEEPALIVE_EXPIRY
        )

        self.client = httpx.AsyncClient(
            base_url=api_base_url,
            timeout=httpx.Timeout(
                connect=settings.TIMEOUT_CONNECT,
                read=settings.TIMEOUT_READ,
                write=settings.TIMEOUT_WRITE,
                pool=settings.TIMEOUT_POOL
            ),
            limits=self.pool_limits,  # Use the stored attribute here
            transport=httpx.AsyncHTTPTransport(
                retries=settings.RETRY_NETWORK_FAILURES,
            ),
            event_hooks = {"request": [log_request]},
        )

        # Connection health monitoring
        self._connection_stats = {
            "total_requests": 0,
            "failed_requests": 0,
            "last_health_check": 0,
            "avg_response_time": 0.0
        }

        # Keep last N response times for rolling average
        self._response_times = deque(maxlen=settings.MAX_REQUEST_ROLLING_RETRIES)  # rolling window of 100 requests

        log.info('✅ Enhanced HTTP client initialized with optimized connection pooling')

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the backend service
        without relying on httpx internal attributes.
        """
        try:
            start_time = get_start_time()
            response = await self.client.get("/actuator/health")  # Common health endpoint
            response_time = time.time() - start_time

            self._connection_stats["last_health_check"] = time.time()

            return {
                "status": "healthy" if response.is_success else "unhealthy",
                "response_time_seconds": response_time,
                "status_code": response.status_code,
            }
        except Exception as e:
            log.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics and performance metrics
        (safe version without private httpx internals).
        """
        health = await self.health_check()

        stats = {
            "connection_pool": {
                # 2. Reference self.pool_limits instead of self.client.limits
                "max_connections": self.pool_limits.max_connections,
                "max_keepalive_connections": self.pool_limits.max_keepalive_connections,
                "keepalive_expiry_seconds": self.pool_limits.keepalive_expiry
            },
            "performance": {
                "total_requests": self._connection_stats["total_requests"],
                "failed_requests": self._connection_stats["failed_requests"],
                "success_rate": self._calculate_success_rate(),
                "avg_response_time": round(self._connection_stats["avg_response_time"], 3),
                "last_health_check": self._connection_stats["last_health_check"],
            },
            "backend_health": health
        }

        return stats

    def _calculate_success_rate(self) -> float:
        """Calculate request success rate"""
        total = self._connection_stats["total_requests"]
        if total == 0:
            return 100.0
        failed = self._connection_stats["failed_requests"]
        return ((total - failed) / total) * 100

    def _update_stats(self, success: bool, response_time: float):
        """Update connection statistics with rolling average response time"""
        self._connection_stats["total_requests"] += 1
        if not success:
            self._connection_stats["failed_requests"] += 1

        # Add response time to rolling window
        self._response_times.append(response_time)

        # Update rolling average
        if self._response_times:
            self._connection_stats["avg_response_time"] = (
                sum(self._response_times) / len(self._response_times)
            )

    @CIRCUIT
    async def get_candidate_results(self, candidate_id: str, token: str) -> str:
        start_time = get_start_time()
        try:

            res = await self.client.get("internal/chat-sessions/findCandidateFinalResultsForBot",
                params={"idCandidat": candidate_id},
                headers=_auth_headers(token),
            )

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return res.text
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

    @CIRCUIT
    async def get_faq_by_label_intent(self, intent: str):
        start_time = get_start_time()
        try:
            res = await self.client.get("aichatbot/getFaqByLabelIntent", params={"intentLabel": intent})
            response_time = time.time() - start_time
            self._update_stats(True, response_time)
            return res.text
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

    @CIRCUIT
    async def save_feedback(self, payload):
        start_time = get_start_time()
        try:
            res = await self.client.post("aichatbot/feedback", json=payload)
            response_time = time.time() - start_time
            self._update_stats(True, response_time)
            return res.text
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

    @CIRCUIT
    async def get_dynamic_response(self, payload) -> List[Dict[str, Any]]:
        start_time = get_start_time()
        try:
            res = await self.client.post("aichatbot/get-dynamic-response", json=payload)


            # Log the full URL actually requested
            log.info("Full endpoint URL: %s", res.request.url)
            log.info("HTTP status: %s", res.status_code)
            log.info("Response body: %s", res.text)
            res.raise_for_status()

            response_time = time.time() - start_time
            self._update_stats(True, response_time)
            return res.json()
        except Exception as e:
            response_time = time.time() - start_time
            log.exception(e)
            self._update_stats(False, response_time)
            raise


    @CIRCUIT
    async def get_next_detailed_response(self, user_id):
        start_time = get_start_time()
        try:
            res = await self.client.get("aichatbot/get-next-detailed-response", params={"userId": user_id})
            response_time = time.time() - start_time
            self._update_stats(True, response_time)
            return res.text
        except Exception as e:
            response_time = time.time() - start_time
            log.exception(e)
            self._update_stats(False, response_time)
            raise


    @CIRCUIT
    async def find_final_results_for_bot_by_intent_and_candidat_id(self, flow_intent, candidat_id, token):
        start_time = get_start_time()
        try:

            res = await self.client.get("internal/chat-sessions/findFinalResultsForBotByIntentFlowAndCandidatId",
                                        params={"intentFlow": flow_intent, "candidatId": candidat_id},
                                        headers=_auth_headers(token))

            log.info("____________________________________ 1")
            log.info(candidat_id)
            log.info(flow_intent)
            log.info(res)
            log.info("____________________________________ 2")
            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return res
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

    @CIRCUIT
    async def congrat_final_results_by_id_candidat(self, candidat_id, token):
        start_time = get_start_time()
        try:

            res = await self.client.get("internal/chat-sessions/congratFinalResultsByIdCandidat",
                                        params={"candidatId": candidat_id},
                                        headers=_auth_headers(token))

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return res
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

    @CIRCUIT
    async def get_info_by_button_label(self, payload) -> str:
        start_time = get_start_time()
        try:
            res = await self.client.post("aichatbot/get-info-by-button-label", json=payload)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return res.text
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

    @CIRCUIT
    async def get_chat_session_identity(self, payload, token):
        start_time = get_start_time()
        try:
            res = await self.client.post("internal/chat-sessions/identity", json=payload, headers=_auth_headers(token))
            response_time = time.time() - start_time
            self._update_stats(True, response_time)
            return res.text if res.status_code == 200 else None
        except Exception as e:
            log.exception(e)
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            raise

# Add context manager support for better resource management
class ManagedHttpResultsService(HttpResultsService):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Properly close the client and cleanup connections"""
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()
            log.info("🔌 HTTP client closed gracefully")