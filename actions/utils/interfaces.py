"""
actions/utils/interfaces.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from httpx import Response

class IResultsService(ABC):

    @abstractmethod
    async def get_candidate_results(self, candidate_id: str, token: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_faq_by_label_intent(self, intent: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def save_feedback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_dynamic_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def find_final_results_for_bot_by_intent_and_candidat_id(self, intent, candidat_id, token) -> Response:
        pass

    @abstractmethod
    async def congrat_final_results_by_id_candidat(self, candidat_id, token) -> Response:
        pass

    @abstractmethod
    async def get_info_by_button_label(self, payload: Dict[str, Any]) -> Response:
        pass

    @abstractmethod
    async def get_chat_session_identity(self, payload: Dict[str, Any], token) -> Response:
        pass

    @abstractmethod
    async def get_next_detailed_response(self, user_id) -> str:
        pass
