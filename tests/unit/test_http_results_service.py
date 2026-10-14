"""
tests/unit/test_http_results_service.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.utils.services import HttpResultsService

import pytest


@pytest.mark.asyncio
async def test_http_failure(monkeypatch):

    service = HttpResultsService()

    async def fake_get(*_args, **_kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(service.client, "get", fake_get)

    with pytest.raises(RuntimeError):
        await service.get_faq_by_label_intent("intent")

@pytest.mark.asyncio
async def test_health_check_success(monkeypatch):
    service = HttpResultsService()

    async def fake_get(*_args, **_kwargs):
        class R:
            status_code = 200
            is_success = True
        return R()

    monkeypatch.setattr(service.client, "get", fake_get)

    res = await service.health_check()
    assert res["status"] == "healthy"