"""
actions/utils/test_services.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from collections import deque
from typing import List, Dict, Any
from aiocircuitbreaker import circuit
from actions.authentication.credentials import InvalidCredentialsError, validate_jwt_before_use
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
async def _validate_jwt_before_request(token: str) -> bool:
    return validate_jwt_before_use(token.strip().replace("Bearer ", "").lstrip("."))


class HttpResultsService(IResultsService):
    def __init__(self):
        # 1. Store the limits in a dedicated attribute
        self.pool_limits = httpx.Limits(
            max_connections=settings.MAX_CONNECTIONS,
            max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=settings.KEEPALIVE_EXPIRY
        )

        self.client = httpx.AsyncClient(
            base_url=API_URL,
            timeout=httpx.Timeout(
                connect=settings.TIMEOUT_CONNECT,
                read=settings.TIMEOUT_READ,
                write=settings.TIMEOUT_WRITE,
                pool=settings.TIMEOUT_POOL
            ),
            limits=self.pool_limits,  # Use the stored attribute here
            transport=httpx.AsyncHTTPTransport(
                retries=settings.RETRY_NETWORK_FAILURES,
            )
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
            # Validate JWT before making the request
            if not await _validate_jwt_before_request(token):
                raise RuntimeError(f"Invalid or expired JWT token: {token}")

            res = await self.client.get(
                "/findCandidateFinalResultsForBot",
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
            res = await self.client.get("/getFaqByLabelIntent", params={"intentLabel": intent})
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
            res = await self.client.post("/feedback", json=payload)
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
            res = await self.client.post("/get-dynamic-response", json=payload)
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
            res = await self.client.get("/get-next-detailed-response", params={"userId": user_id})
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
            if not await _validate_jwt_before_request(token):
                raise RuntimeError(f"Invalid or expired JWT token: {token}")

            res = await self.client.get("/findFinalResultsForBotByIntentFlowAndCandidatId",
                                        params={"intentFlow": flow_intent, "candidatId": candidat_id},
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
    async def congrat_final_results_by_id_candidat(self, candidat_id, token):
        start_time = get_start_time()
        try:
            # Validate JWT before making the request
            if not await _validate_jwt_before_request(token):
                raise RuntimeError(f"Invalid or expired JWT token: {token}")

            res = await self.client.get("/congratFinalResultsByIdCandidat",
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
    async def verif_credentials(self, payload: dict) -> dict:
        start_time = get_start_time()
        try:
            response = await self.client.post("/verifCredentials", json=payload)
            response_time = time.time() - start_time

            if response.status_code == 401:
                self._update_stats(True, response_time)  # 401 is expected for wrong credentials
                raise InvalidCredentialsError("Invalid username or password")

            response.raise_for_status()
            self._update_stats(True, response_time)

            return response.json()
        except Exception as e:
            response_time = time.time() - start_time
            if not isinstance(e, InvalidCredentialsError):
                self._update_stats(False, response_time)
            raise

    async def get_jwt_token(self):
        if hasattr(self, "token") and self.token:
            return self.token
        raise RuntimeError("JWT token is missing. Authenticate first.")

    @CIRCUIT
    async def get_info_by_button_label(self, payload) -> str:
        start_time = get_start_time()
        try:
            res = await self.client.post("/get-info-by-button-label", json=payload)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return res.text
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