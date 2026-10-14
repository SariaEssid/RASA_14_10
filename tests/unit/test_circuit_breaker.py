"""
tests/unit/test_circuit_breaker.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import pytest

from actions.utils.services import HttpResultsService

@pytest.mark.asyncio
async def test_circuit_breaker_open_state(monkeypatch):

    service = HttpResultsService()

    async def fail(*_args, **_kwargs):
        raise RuntimeError("service down")

    monkeypatch.setattr(service.client, "get", fail)

    with pytest.raises(RuntimeError):
        await service.get_faq_by_label_intent("x")


@pytest.mark.asyncio
async def test_circuit_breaker_recovery(monkeypatch):

    service = HttpResultsService()

    call_count = {"n": 0}

    async def flaky(*_args, **_kwargs):
        call_count["n"] += 1
        return type("R", (), {"text": "ok", "status_code": 200})()

    monkeypatch.setattr(service.client, "get", flaky)

    result = await service.get_faq_by_label_intent("x")

    assert result == "ok"
    assert call_count["n"] >= 1